#stream.py
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

from scipy.signal import savgol_filter

from collections import OrderedDict

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

            bpm_files, uterus_files = [], []

            if os.path.isdir(bpm_dir):
                for fname in sorted(os.listdir(bpm_dir)):
                    if fname.lower().endswith(".csv"):
                        bpm_files.append(os.path.join(bpm_dir, fname))

            if os.path.isdir(uter_dir):
                for fname in sorted(os.listdir(uter_dir)):
                    if fname.lower().endswith(".csv"):
                        uterus_files.append(os.path.join(uter_dir, fname))

            if not bpm_files and not uterus_files:
                continue

            sid = folder  

            si = SessionInfo(
                group=group,
                folder_id=folder,
                session_id=sid,
                bpm_files=sorted(bpm_files),
                uterus_files=sorted(uterus_files),
            )

            logger.info(f"Сессия {sid}: {len(bpm_files)} BPM файлов, {len(uterus_files)} Uterus файлов")
            sessions[sid] = si

    logger.info(f"Найдено {len(sessions)} сессий")
    return sessions

    """
    Ищет все доступные сессии в папке data_root.
    Структура:
      data_root/{group}/{folder}/{bpm,uterus}/*.csv
    session_id берется из основной части имени файла до последнего подчеркивания
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
            for dpath, dtype in [(bpm_dir, "bpm"), (uter_dir, "uterus")]:
                if not os.path.isdir(dpath):
                    logger.warning(f"Папка {dpath} не существует")
                    continue
                    
                for fname in sorted(os.listdir(dpath)):
                    if not fname.lower().endswith(".csv"):
                        continue
                    
                    # Извлекаем session_id: берем часть до последнего подчеркивания
                    # Например: 20250908-07500001_1.csv → 20250908-07500001
                    if '_' in fname:
                        session_prefix = fname.rsplit('_', 1)[0]
                    else:
                        session_prefix = fname.split('.')[0]  # если нет подчеркивания
                    
                    files_by_session.setdefault(session_prefix, {"bpm": [], "uterus": []})
                    full_path = os.path.join(dpath, fname)
                    files_by_session[session_prefix][dtype].append(full_path)
                    
                    logger.info(f"Найден файл: {full_path} → session: {session_prefix}")

            # Создаем SessionInfo для каждой сессии
            for sid, filemap in files_by_session.items():
                # Сортируем файлы по имени (чтобы шли в правильном порядке)
                bpm_files = sorted(filemap.get("bpm", []))
                uterus_files = sorted(filemap.get("uterus", []))
                
                si = SessionInfo(
                    group=group,
                    folder_id=folder,
                    session_id=sid,
                    bpm_files=bpm_files,
                    uterus_files=uterus_files,
                )
                
                # Логируем информацию о найденных файлах
                logger.info(f"Сессия {sid}: {len(bpm_files)} BPM файлов, {len(uterus_files)} uterus файлов")
                for bpm_file in bpm_files:
                    logger.info(f"  BPM: {os.path.basename(bpm_file)}")
                for uterus_file in uterus_files:
                    logger.info(f"  Uterus: {os.path.basename(uterus_file)}")
                
                sessions[sid] = si

    logger.info(f"Найдено {len(sessions)} сессий")
    return sessions


# --------------------
# Сборка CSV в единый временной ряд
# --------------------
def read_and_concat_files(file_list: List[str], time_col: str = "time_sec", value_col: str = "value") -> pd.DataFrame:
    """
    Склеивает несколько файлов подряд.
    Следующий файл начинается сразу после конца предыдущего.
    """
    if not file_list:
        return pd.DataFrame(columns=["time", "value"])

    parts = []
    time_offset = 0.0

    for idx, fp in enumerate(sorted(file_list)):
        df = pd.read_csv(fp, usecols=[time_col, value_col])
        if df.empty:
            continue

        df = df.rename(columns={time_col: "time", value_col: "value"})
        df = df.dropna()

        # нормализуем время внутри файла: начинаем с 0
        df["time"] = df["time"] - df["time"].iloc[0]

        # сдвигаем на накопленный offset
        df["time"] += time_offset

        # обновляем offset для следующего файла
        time_offset = df["time"].iloc[-1] + (df["time"].iloc[1] - df["time"].iloc[0])

        parts.append(df)

        logger.info(f"{os.path.basename(fp)}: {len(df)} точек, глобальное время {df['time'].iloc[0]:.2f}–{df['time'].iloc[-1]:.2f}")

    return pd.concat(parts, ignore_index=True)





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

    # ---- 1. Проверка кэша ----
    cache_key = f"{session.session_id}_{sample_rate}_{median_kernel}_{ema_span}"
    if cache_key in SESSION_CACHE:
        logger.info(f"Используем кэш для {cache_key}")
        return SESSION_CACHE[cache_key]

    # ---- 2. Чтение CSV ----
    bpm_df = read_and_concat_files(session.bpm_files)
    uter_df = read_and_concat_files(session.uterus_files)

    # ---- 3. Ресемплинг и объединение ----
    merged, warnings = resample_and_merge(
        bpm_df, uter_df,
        sample_rate=sample_rate,
        interp_limit_s=interp_limit_s,
        gap_warn_s=gap_warn_s
    )

    # ---- 4. Фильтрация bpm ----
    if merged["bpm"].notna().any():
        bpm_proc = enhanced_preprocessing(
            merged["bpm"].to_numpy(),
            median_kernel=median_kernel,
            ema_span=ema_span
        )
        merged["bpm_filtered"] = bpm_proc["filtered"]
        merged["bpm_baseline"] = bpm_proc["baseline"]
        merged["bpm_smooth"] = bpm_proc["smooth"]
        merged["bpm_deviation"] = bpm_proc["deviation"]

    # ---- 5. Фильтрация uterus ----
    if merged["uterus"].notna().any():
        uter_proc = enhanced_preprocessing(
            merged["uterus"].to_numpy(),
            median_kernel=median_kernel,
            ema_span=ema_span
        )
        merged["uterus_filtered"] = uter_proc["filtered"]
        merged["uterus_baseline"] = uter_proc["baseline"]
        merged["uterus_smooth"] = uter_proc["smooth"]
        merged["uterus_deviation"] = uter_proc["deviation"]

    # ---- 6. Метаданные ----
    meta = {
        "session_id": session.session_id,
        "group": session.group,
        "folder_id": session.folder_id,
        "start_time": float(merged["time"].iloc[0]) if not merged.empty else None,
        "end_time": float(merged["time"].iloc[-1]) if not merged.empty else None,
    }

    result = {
        "session": session,
        "merged": merged,
        "warnings": warnings,
        "meta": meta
    }

    # ---- 7. Сохраняем в кэш ----
    SESSION_CACHE[cache_key] = result
    logger.info(f"Сессия {cache_key} добавлена в кэш")

    return result


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



# --------------------
# Ограниченный кэш сессий (FIFO)
# --------------------
class SessionCache(OrderedDict):
    def __init__(self, maxsize: int = 20):
        super().__init__()
        self.maxsize = maxsize

    def __setitem__(self, key, value):
        if key in self:
            del self[key]  # обновляем порядок
        elif len(self) >= self.maxsize:
            self.popitem(last=False)  # удаляем самую старую
        super().__setitem__(key, value)


SESSION_CACHE = SessionCache(maxsize=20)


# Запуск напрямую (если не через Docker)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=False)

def enhanced_preprocessing(arr: np.ndarray, median_kernel: int = 3, ema_span: int = 20, sg_window: int = 7, sg_poly: int = 2) -> Dict[str, np.ndarray]:
    """
    Усиленная предобработка сигнала:
    - медианный фильтр
    - удаление спайков
    - EMA baseline
    - Savitzky-Golay сглаживание
    """
    arr_filtered = apply_median_filter(arr, kernel=median_kernel)
    arr_filtered = remove_spikes(arr_filtered)
    baseline = apply_ema(arr_filtered, span=ema_span)
    arr_smooth = savgol_filter(arr_filtered, window_length=sg_window, polyorder=sg_poly, mode='interp')
    
    return {
        "filtered": arr_filtered,
        "baseline": baseline,
        "smooth": arr_smooth,
        "deviation": arr_filtered - baseline
    }



