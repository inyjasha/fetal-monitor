"""
ml-service/main.py

Сервис на FastAPI, который:
 - сканирует структуру папок data/ (группы hypoxia / regular),
 - собирает все CSV одной сессии (bpm + uterus) в единый временной ряд,
 - выполняет предобработку (медианный фильтр, удаление спайков, EMA baseline),
 - заполняет небольшие пропуски интерполяцией,
 - выдает API для получения списка сессий, метаданных и потоковых данных (WebSocket).
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Включаем базовое логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ml-service")

# Корневая папка с данными (внутри ml-service/data)
DATA_ROOT = os.path.join(os.path.dirname(__file__), "data")
# Две группы пациентов с гипоксией и без
GROUPS = ["hypoxia", "regular"]


# --------------------
# Модель данных для описания одной сессии
# --------------------
class SessionInfo(BaseModel):
    group: str          # hypoxia | regular
    folder_id: str      # папка пациента (например "1")
    session_id: str     # ID сессии (например 20250908-07500001)
    bpm_files: List[str]
    uterus_files: List[str]
    start_time: Optional[float] = None
    end_time: Optional[float] = None


# --------------------
# Сканирование папок сессий
# --------------------
def scan_sessions(data_root: str = DATA_ROOT) -> Dict[str, SessionInfo]:
    """
    Ищет все доступные сессии в папке data_root.
    Структура:
      data_root/{group}/{folder}/{bpm,uterus}/*.csv
    session_id берется из префикса имени файла: 20250908-07500001_1.csv → 20250908-07500001
    """
    sessions: Dict[str, SessionInfo] = {}
    for group in GROUPS:
        grp_path = os.path.join(data_root, group)
        if not os.path.isdir(grp_path):
            continue
        for folder in sorted(os.listdir(grp_path)):
            folder_path = os.path.join(grp_path, folder)
            if not os.path.isdir(folder_path):
                continue

            bpm_dir = os.path.join(folder_path, "bpm")
            uter_dir = os.path.join(folder_path, "uterus")

            files_by_session = {}
            # Собираем bpm и uterus файлы
            for dpath, dtype in ((bpm_dir, "bpm"), (uter_dir, "uterus")):
                if not os.path.isdir(dpath):
                    continue
                for fname in sorted(os.listdir(dpath)):
                    if not fname.lower().endswith(".csv"):
                        continue
                    # Берем часть имени файла до "_" → session_id
                    session_prefix = fname.split("_")[0]
                    files_by_session.setdefault(session_prefix, {"bpm": [], "uterus": []})
                    files_by_session[session_prefix][dtype].append(os.path.join(dpath, fname))

            # Создаем SessionInfo для каждой сессии
            for sid, filemap in files_by_session.items():
                si = SessionInfo(
                    group=group,
                    folder_id=folder,
                    session_id=sid,
                    bpm_files=sorted(filemap.get("bpm", [])),
                    uterus_files=sorted(filemap.get("uterus", [])),
                )
                sessions[sid] = si

    logger.info(f"Найдено {len(sessions)} сессий")
    return sessions


# --------------------
# Сборка CSV в единый временной ряд
# --------------------
def read_and_concat_files(file_list: List[str], time_col: str = "time_sec", value_col: str = "value") -> pd.DataFrame:
    """
    Каждый CSV файл обычно начинается с time_sec = 0.
    Объединяем файлы, смещая время так, чтобы получился непрерывный ряд.
    Возвращает DataFrame с колонками ["time", "value"].
    """
    if not file_list:
        return pd.DataFrame(columns=["time", "value"])

    parts = []
    offset = 0.0
    for fp in file_list:
        try:
            df = pd.read_csv(fp, usecols=[time_col, value_col])
        except Exception as e:
            logger.warning(f"Ошибка чтения {fp}: {e}")
            continue
        df = df.rename(columns={time_col: "time", value_col: "value"})
        df["time"] = pd.to_numeric(df["time"], errors="coerce")
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

        if df.empty:
            continue

        # Если файл начинается с 0 → добавляем смещение
        if df["time"].iloc[0] <= 1.0:
            df["time"] += offset
            offset = float(df["time"].iloc[-1]) + (np.median(np.diff(df["time"])) if len(df) > 1 else 0.0)
        else:
            # Если уже абсолютные времена → корректируем при необходимости
            if df["time"].iloc[0] < offset:
                shift = offset - df["time"].iloc[0] + 0.001
                df["time"] += shift
            offset = float(df["time"].iloc[-1])

        parts.append(df[["time", "value"]])

    if not parts:
        return pd.DataFrame(columns=["time", "value"])

    return pd.concat(parts, ignore_index=True).sort_values("time").reset_index(drop=True)


# --------------------
# Простейшие фильтры для очистки сигнала
# --------------------
def apply_median_filter(arr: np.ndarray, kernel: int = 3) -> np.ndarray:
    """Медианный фильтр (убирает одиночные шумовые выбросы)."""
    return pd.Series(arr).rolling(window=kernel, center=True, min_periods=1).median().to_numpy()


def apply_ema(arr: np.ndarray, span: int = 20) -> np.ndarray:
    """Экспоненциальное скользящее среднее (для baseline)."""
    return pd.Series(arr).ewm(span=span, adjust=False).mean().to_numpy()


def remove_spikes(arr: np.ndarray, thresh_std: float = 4.0) -> np.ndarray:
    """Удаление сильных выбросов (спайков)."""
    med = np.nanmedian(arr)
    std = np.nanstd(arr)
    if std == 0 or np.isnan(std):
        return arr
    out = arr.copy()
    spike_mask = np.abs(arr - med) > (thresh_std * std)
    for i in np.where(spike_mask)[0]:
        lo, hi = max(0, i - 2), min(len(arr), i + 3)
        out[i] = np.nanmedian(arr[lo:hi])
    return out


# --------------------
# Ресемплинг и объединение сигналов
# --------------------
def resample_and_merge(bpm_df: pd.DataFrame, uter_df: pd.DataFrame, sample_rate: float = 4.0,
                       interp_limit_s: float = 5.0, gap_warn_s: float = 10.0) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    Приводим bpm и uterus к равномерной сетке времени.
    - интерполируем пропуски до interp_limit_s секунд,
    - большие разрывы оставляем как NaN и логируем предупреждения.
    """
    warnings = []
    start, end = None, None
    for d in (bpm_df, uter_df):
        if not d.empty:
            start = d["time"].iloc[0] if start is None else min(start, d["time"].iloc[0])
            end = d["time"].iloc[-1] if end is None else max(end, d["time"].iloc[-1])

    if start is None:
        return pd.DataFrame(columns=["time", "bpm", "uterus"]), warnings

    step = 1.0 / sample_rate
    time_index = np.arange(start, end + 0.0001, step)
    out = pd.DataFrame({"time": time_index})

    # Функция для ресемплинга одного сигнала
    def reindex_and_interp(src: pd.DataFrame):
        if src.empty:
            return pd.Series(index=out.index, dtype=float)
        s = src.set_index("time")["value"]
        s = s[~s.index.duplicated(keep="first")]
        s_reindexed = s.reindex(s.index.union(out["time"])).sort_index()
        s_interp = s_reindexed.interpolate(method="index", limit_direction="both")
        return s_interp.reindex(out["time"]).to_numpy()

    out["bpm"] = reindex_and_interp(bpm_df)
    out["uterus"] = reindex_and_interp(uter_df)

    # Проверяем пропуски
    def detect_large_gaps(series, name):
        nan_mask = np.isnan(series.to_numpy())
        if not nan_mask.any():
            return
        i, n = 0, len(nan_mask)
        while i < n:
            if nan_mask[i]:
                j = i
                while j < n and nan_mask[j]:
                    j += 1
                gap_seconds = (j - i) * step
                if gap_seconds > gap_warn_s:
                    warnings.append({"type": "large_gap", "signal": name, "from": out["time"].iloc[i],
                                     "to": out["time"].iloc[j - 1], "gap_s": gap_seconds})
                i = j
            else:
                i += 1

    detect_large_gaps(out["bpm"], "bpm")
    detect_large_gaps(out["uterus"], "uterus")

    return out, warnings


# --------------------
# Основной пайплайн обработки сессии
# --------------------
def prepare_session(session: SessionInfo, sample_rate: float = 4.0,
                    median_kernel: int = 3, ema_span: int = 20,
                    interp_limit_s: float = 5.0, gap_warn_s: float = 10.0) -> Dict:
    """
    Читает данные одной сессии, обрабатывает и возвращает:
    {
      "session": SessionInfo,
      "merged": DataFrame(time,bpm,uterus,bpm_filtered,...),
      "warnings": [...],
      "meta": {...}
    }
    """
    bpm_df = read_and_concat_files(session.bpm_files)
    uter_df = read_and_concat_files(session.uterus_files)

    merged, warnings = resample_and_merge(bpm_df, uter_df, sample_rate=sample_rate,
                                          interp_limit_s=interp_limit_s, gap_warn_s=gap_warn_s)

    # Фильтрация bpm
    if merged["bpm"].notna().any():
        arr = apply_median_filter(merged["bpm"].to_numpy(), kernel=median_kernel)
        arr = remove_spikes(arr)
        merged["bpm_filtered"] = arr
        merged["bpm_baseline"] = apply_ema(arr, span=ema_span)

    # Фильтрация uterus
    if merged["uterus"].notna().any():
        arr = apply_median_filter(merged["uterus"].to_numpy(), kernel=median_kernel)
        arr = remove_spikes(arr)
        merged["uterus_filtered"] = arr
        merged["uterus_baseline"] = apply_ema(arr, span=ema_span)

    meta = {
        "session_id": session.session_id,
        "group": session.group,
        "folder_id": session.folder_id,
        "start_time": float(merged["time"].iloc[0]) if not merged.empty else None,
        "end_time": float(merged["time"].iloc[-1]) if not merged.empty else None,
    }

    return {"session": session, "merged": merged, "warnings": warnings, "meta": meta}


# --------------------
# API FastAPI
# --------------------
app = FastAPI(title="Fetal Monitor ML Service")

@app.get("/sessions")
async def list_sessions():
    """Вернуть список доступных сессий."""
    sessions = scan_sessions()
    return [{"session_id": sid, "group": info.group, "folder_id": info.folder_id}
            for sid, info in sessions.items()]


@app.get("/sessions/{sid}")
async def session_info(sid: str, sample_rate: float = Query(4.0, description="Частота выборки, Гц")):
    """Метаданные и предупреждения по конкретной сессии."""
    sessions = scan_sessions()
    if sid not in sessions:
        raise HTTPException(status_code=404, detail="session not found")
    prepared = prepare_session(sessions[sid], sample_rate=sample_rate)
    return {"meta": prepared["meta"], "n_samples": len(prepared["merged"]), "warnings": prepared["warnings"]}


@app.websocket("/ws/stream/{sid}")
async def ws_stream(websocket: WebSocket, sid: str, sample_rate: float = 4.0):
    """
    Стрим данных через WebSocket.
    Отправляем JSON с каждым шагом (имитация реального времени).
    """
    await websocket.accept()
    sessions = scan_sessions()
    if sid not in sessions:
        await websocket.send_json({"error": "session not found"})
        await websocket.close()
        return

    prepared = prepare_session(sessions[sid], sample_rate=sample_rate)
    merged = prepared["merged"]

    # Первое сообщение: метаданные
    await websocket.send_json({"meta": prepared["meta"], "warnings": prepared["warnings"]})

    step = 1.0 / sample_rate
    try:
        for _, row in merged.iterrows():
            payload = {
                "time": float(row["time"]),
                "bpm": None if np.isnan(row.get("bpm", np.nan)) else float(row.get("bpm")),
                "uterus": None if np.isnan(row.get("uterus", np.nan)) else float(row.get("uterus")),
            }
            await websocket.send_json({"frame": payload})
            await asyncio.sleep(step)  # эмуляция реального времени
    except WebSocketDisconnect:
        logger.info("Клиент отключился")


# Запуск напрямую (если не через Docker)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)
