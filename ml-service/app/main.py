import os
import sys
import asyncio
import logging
from typing import Dict

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.ml.predict import compute_session_features

import math


# --------------------
# Логирование
# --------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ml-service")

# Путь к корню проекта
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

# Импортируем функции из stream.py
from app.stream import scan_sessions, prepare_session

# --------------------
# FastAPI app
# --------------------
app = FastAPI(title="Fetal Monitor ML Service")

def clean_for_json(data):
    import math
    import numpy as np

    if isinstance(data, dict):
        return {k: clean_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_for_json(v) for v in data]
    elif isinstance(data, (float, np.floating)):
        if math.isnan(data) or math.isinf(data):
            return None
        return float(data)
    elif isinstance(data, (np.integer,)):
        return int(data)
    else:
        return data


@app.get("/sessions/{sid}/analysis")
def session_analysis(sid: str, sample_rate: float = Query(4.0)):
    sessions = scan_sessions()
    if sid not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    prepared = prepare_session(sessions[sid], sample_rate=sample_rate)
    features = compute_session_features(prepared["merged"])

    clean_features = clean_for_json(features)

    return {"meta": prepared["meta"], "features": clean_features}


# CORS (для фронтенда)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Разрешаем любые источники (на время разработки)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------
# REST endpoints
# --------------------
@app.get("/ping")
def ping():
    return {"msg": "pong"}


@app.get("/sessions")
def list_sessions():
    """Вернуть список доступных сессий"""
    sessions = scan_sessions()
    return [
        {"session_id": sid, "group": info.group, "folder_id": info.folder_id}
        for sid, info in sessions.items()
    ]


@app.get("/sessions/{sid}")
def session_info(sid: str, sample_rate: float = Query(4.0, description="Частота выборки, Гц")):
    """Метаданные по конкретной сессии"""
    sessions = scan_sessions()
    if sid not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    prepared = prepare_session(sessions[sid], sample_rate=sample_rate)
    return {
        "meta": prepared["meta"],
        "n_samples": len(prepared["merged"]),
        "warnings": prepared["warnings"],
    }




# --------------------
# WebSocket streaming
# --------------------
@app.websocket("/ws/stream/{sid}")
async def websocket_stream(websocket: WebSocket, sid: str, sample_rate: float = 4.0):
    """
    Стрим данных через WebSocket.
    Каждое сообщение = один шаг (эмуляция реального времени).
    """
    await websocket.accept()
    sessions = scan_sessions()

    if sid not in sessions:
        await websocket.send_json({"error": f"Session {sid} not found"})
        await websocket.close()
        return

    prepared = prepare_session(sessions[sid], sample_rate=sample_rate)
    merged = prepared["merged"]

    # Отправляем метаданные в начале
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
            await asyncio.sleep(step)  # эмуляция частоты
    except WebSocketDisconnect:
        logger.info(f"Клиент отключился от {sid}")


# --------------------
# Запуск (локально, без Docker)
# --------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
