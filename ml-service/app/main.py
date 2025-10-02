# app/main.py (исправленная версия)

from datetime import datetime
import os
import sys
import asyncio
import logging
from typing import Dict, List, Optional, Any  # ДОБАВЛЕН Any
import json

import numpy as np
import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query

from app.ml.patient_data import patient_manager

from app.ml.report_generator import report_generator
from fastapi.responses import FileResponse
import tempfile

from app.auth import router as auth_router


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

from fastapi.middleware.cors import CORSMiddleware

from app.patients_search import router as patients_router


# --------------------
# FastAPI app
# --------------------
app = FastAPI(title="Fetal Monitor ML Service")

# CORS (для фронтенда)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------
# Вспомогательные функции для анализа
# --------------------
def compute_basic_features(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Упрощенная версия вычисления признаков для анализа сессии.
    """
    bpm = df.get("bpm_filtered", df.get("bpm"))
    uterus = df.get("uterus_filtered", df.get("uterus")) if "uterus" in df else None
    
    # Базовые статистики BPM
    bpm_valid = bpm.dropna()
    
    features = {
        "duration_seconds": float(df["time"].max() - df["time"].min()) if len(df) > 0 else 0,
        "total_samples": len(df),
        "bpm_samples": len(bpm_valid),
        
        # Статистики BPM
        "mean_bpm": float(bpm_valid.mean()) if len(bpm_valid) > 0 else None,
        "median_bpm": float(bpm_valid.median()) if len(bpm_valid) > 0 else None,
        "max_bpm": float(bpm_valid.max()) if len(bpm_valid) > 0 else None,
        "min_bpm": float(bpm_valid.min()) if len(bpm_valid) > 0 else None,
        "std_bpm": float(bpm_valid.std()) if len(bpm_valid) > 0 else None,
        
        # События (упрощенные)
        "decel_count": 0,  # Заглушка
        "tachy_count": len(bpm_valid[bpm_valid > 160]) if len(bpm_valid) > 0 else 0,
        "brady_count": len(bpm_valid[bpm_valid < 110]) if len(bpm_valid) > 0 else 0,
    }
    
    return features

# --------------------
# Вспомогательные классы для предсказаний
# --------------------
class SimpleTrendPredictor:
    """Простой предсказатель трендов"""
    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self.bpm_buffer = []
        self.time_buffer = []
        
    def update(self, time_val: float, bpm_val: Optional[float]):
        if bpm_val is not None and not np.isnan(bpm_val):
            self.time_buffer.append(time_val)
            self.bpm_buffer.append(bpm_val)
            # Ограничиваем размер буфера
            if len(self.time_buffer) > self.window_size:
                self.time_buffer.pop(0)
                self.bpm_buffer.pop(0)
            
    def predict_trend(self) -> Dict:
        if len(self.bpm_buffer) < 10:
            return {"trend": "insufficient_data", "slope": 0.0, "confidence": 0.0}
            
        times = np.array(self.time_buffer)
        bpm = np.array(self.bpm_buffer)
        
        # Линейная регрессия для определения тренда
        try:
            # Центрируем время для численной стабильности
            times_centered = times - np.mean(times)
            
            # Простая линейная регрессия
            if np.sum(times_centered ** 2) == 0:
                slope = 0.0
            else:
                slope = np.sum(times_centered * bpm) / np.sum(times_centered ** 2)
            
            # Определяем тренд
            if slope > 0.05:
                trend = "rising"
            elif slope < -0.05:
                trend = "falling" 
            else:
                trend = "stable"
                
            # Простая оценка уверенности
            confidence = min(1.0, len(self.bpm_buffer) / self.window_size)
            
            return {
                "trend": trend,
                "slope": float(slope),
                "confidence": float(confidence),
                "window_size": len(self.bpm_buffer)
            }
        except Exception as e:
            logger.warning(f"Error in trend prediction: {e}")
            return {"trend": "error", "slope": 0.0, "confidence": 0.0}

class RiskPredictor:
    """Простой классификатор рисков на основе правил"""
    def __init__(self):
        pass
        
    def predict_risk(self, bpm_values: List[float]) -> Dict:
        if len(bpm_values) < 10:
            return {"risk_level": "unknown", "score": 0.0, "factors": []}
            
        current_bpm = bpm_values[-1] if bpm_values else 0
        bpm_std = np.std(bpm_values) if len(bpm_values) > 1 else 0
        
        risk_score = 0.0
        factors = []
        
        # Правила для оценки риска
        if current_bpm > 160:
            risk_score += 0.4
            factors.append("tachycardia")
        elif current_bpm < 110:
            risk_score += 0.5
            factors.append("bradycardia")
            
        if bpm_std > 15:
            risk_score += 0.3
            factors.append("high_variability")
        elif bpm_std < 3:
            risk_score += 0.2
            factors.append("low_variability")
                
        # Определяем уровень риска
        if risk_score >= 0.6:
            risk_level = "high"
        elif risk_score >= 0.3:
            risk_level = "medium"
        else:
            risk_level = "low"
            
        return {
            "risk_level": risk_level,
            "score": float(risk_score),
            "factors": factors,
            "current_bpm": float(current_bpm),
            "variability": float(bpm_std)
        }

def clean_for_json(data):
    """Очистка данных для JSON сериализации"""
    if isinstance(data, dict):
        return {k: clean_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_for_json(v) for v in data]
    elif isinstance(data, (float, np.floating)):
        if np.isnan(data) or np.isinf(data):
            return None
        return float(data)
    elif isinstance(data, (np.integer,)):
        return int(data)
    else:
        return data

# --------------------
# REST endpoints
# --------------------
@app.get("/")
def root():
    return {"message": "Fetal Monitor ML Service"}

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

@app.get("/sessions/{sid}/analysis")
def session_analysis(sid: str, sample_rate: float = Query(4.0)):
    """Анализ сессии с учетом данных пациентки"""
    sessions = scan_sessions()
    if sid not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    prepared = prepare_session(sessions[sid], sample_rate=sample_rate)
    df = prepared["merged"]

    # Получаем данные пациентки
    session_info = sessions[sid]
    patient_info = patient_manager.get_patient_info(
        session_info.folder_id, 
        session_info.group
    )

    # Вычисляем фичи с учетом данных пациентки
    features = compute_basic_features(df)
    
    # Добавляем информацию о пациентке в ответ
    response_data = {
        "meta": prepared["meta"],
        "features": features,
        "patient_info": {
            "age": patient_info.get("age"),
            "gestation_weeks": patient_info.get("gestation_weeks"),
            "diagnosis": patient_info.get("diagnosis"),
            "has_diabetes": patient_info.get("has_diabetes"),
            "has_anemia": patient_info.get("has_anemia"),
            "has_hypertension": patient_info.get("has_hypertension"),
            "risk_factors": patient_info.get("risk_factors", {}),
            # Добавляем медицинские показатели
            "Ph": patient_info.get("Ph"),
            "Glu": patient_info.get("Glu"), 
            "LAC": patient_info.get("LAC"),
            "BE": patient_info.get("BE"),
            "CO2": patient_info.get("CO2")
        }
    }

    clean_response = clean_for_json(response_data)
    return clean_response

@app.get("/sessions/{sid}/patient-info")
def get_patient_info(sid: str):
    """Получить медицинскую информацию о пациентке"""
    sessions = scan_sessions()
    if sid not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_info = sessions[sid]
    patient_info = patient_manager.get_patient_info(
        session_info.folder_id, 
        session_info.group
    )
    
    return {
        "session_id": sid,
        "folder_id": session_info.folder_id,
        "group": session_info.group,
        "patient_info": patient_info
    }

@app.get("/sessions/{sid}/data")
def get_session_data(
    sid: str, 
    sample_rate: float = Query(4.0, description="Частота выборки, Гц"),
    limit: int = Query(100, description="Лимит точек")
):
    """Получить данные сессии (для отладки)"""
    sessions = scan_sessions()
    if sid not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    prepared = prepare_session(sessions[sid], sample_rate=sample_rate)
    df = prepared["merged"].head(limit)
    
    # Конвертируем DataFrame в список словарей
    data = []
    for _, row in df.iterrows():
        data.append({
            "time": float(row["time"]),
            "bpm": None if pd.isna(row.get("bpm")) else float(row.get("bpm")),
            "uterus": None if pd.isna(row.get("uterus")) else float(row.get("uterus")),
        })
    
    return {
        "meta": prepared["meta"],
        "data": data,
        "total_samples": len(prepared["merged"])
    }

# --------------------
# WebSocket streaming с предсказаниями
# --------------------
@app.websocket("/ws/stream/{sid}")
async def websocket_stream(websocket: WebSocket, sid: str, sample_rate: float = 4.0):
    """
    УЛУЧШЕННЫЙ стрим данных с предсказаниями.
    """
    await websocket.accept()
    sessions = scan_sessions()

    if sid not in sessions:
        await websocket.send_json({"error": f"Session {sid} not found"})
        await websocket.close()
        return

    prepared = prepare_session(sessions[sid], sample_rate=sample_rate)
    merged = prepared["merged"]

    # Инициализируем предсказатели
    trend_predictor = SimpleTrendPredictor(window_size=100)
    risk_predictor = RiskPredictor()
    
    # Буфер для анализа
    bpm_buffer = []
    prediction_interval = 5.0  # секунды между предсказаниями
    last_prediction_time = 0.0

    # Отправляем метаданные в начале
    await websocket.send_json({
        "type": "meta",
        "meta": prepared["meta"], 
        "warnings": prepared["warnings"]
    })

    step = 1.0 / sample_rate
    
    try:
        for _, row in merged.iterrows():
            current_time = float(row["time"])
            bpm_val = None if np.isnan(row.get("bpm", np.nan)) else float(row.get("bpm"))
            uterus_val = None if np.isnan(row.get("uterus", np.nan)) else float(row.get("uterus"))
            
            # Основной фрейм данных
            payload = {
                "type": "frame",
                "time": current_time,
                "bpm": bpm_val,
                "uterus": uterus_val,
            }
            await websocket.send_json(payload)

            # Обновляем предсказатели
            if bpm_val is not None:
                trend_predictor.update(current_time, bpm_val)
                bpm_buffer.append(bpm_val)
                # Ограничиваем размер буфера
                if len(bpm_buffer) > 200:
                    bpm_buffer.pop(0)

            # Отправляем предсказания каждые 5 секунд
            if current_time - last_prediction_time >= prediction_interval and len(bpm_buffer) >= 10:
                # Трендовое предсказание
                trend_pred = trend_predictor.predict_trend()
                
                # Предсказание рисков
                risk_pred = risk_predictor.predict_risk(bpm_buffer)
                
                # Вычисляем текущую статистику
                current_stats = {
                    "mean_bpm_1min": float(np.mean(bpm_buffer[-60:])) if len(bpm_buffer) >= 60 else float(np.mean(bpm_buffer)),
                    "median_bpm_1min": float(np.median(bpm_buffer[-60:])) if len(bpm_buffer) >= 60 else float(np.median(bpm_buffer)),
                    "current_bpm": bpm_val,
                    "samples_in_buffer": len(bpm_buffer)
                }
                
                # Отправляем пакет предсказаний
                prediction_packet = {
                    "type": "prediction",
                    "timestamp": current_time,
                    "trend": trend_pred,
                    "risk": risk_pred,
                    "statistics": current_stats
                }
                await websocket.send_json(prediction_packet)
                
                last_prediction_time = current_time

            await asyncio.sleep(step)

    except WebSocketDisconnect:
        logger.info(f"Клиент отключился от {sid}")
    except Exception as e:
        logger.error(f"Ошибка в WebSocket потоке: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})

app.include_router(auth_router)
app.include_router(patients_router)

@app.get("/sessions/{sid}/report")
def generate_session_report(sid: str):
    """Генерирует PDF отчет по сессии"""
    sessions = scan_sessions()
    if sid not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Получаем данные для отчета
    session_info = sessions[sid]
    
    # Получаем анализ сессии
    prepared = prepare_session(session_info, sample_rate=4.0)
    analysis_data = {
        "meta": prepared["meta"],
        "features": compute_basic_features(prepared["merged"])
    }
    
    # Получаем информацию о пациентке
    patient_info = patient_manager.get_patient_info(
        session_info.folder_id, 
        session_info.group
    )
    
    # Подготавливаем данные сессии
    session_data = {
        "session_id": sid,
        "group": session_info.group,
        "folder_id": session_info.folder_id
    }
    
    try:
        # Генерируем PDF отчет
        pdf_path = report_generator.generate_session_report(
            session_data=session_data,
            analysis_data=analysis_data,
            patient_info=patient_info
        )
        
        # Возвращаем файл
        return FileResponse(
            pdf_path,
            media_type='application/pdf',
            filename=f"session_report_{sid}_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
        
    except Exception as e:
        logger.error(f"Ошибка генерации отчета: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации отчета: {str(e)}")

@app.get("/sessions/{sid}/report-preview")
def get_report_preview(sid: str):
    """Возвращает данные для предварительного просмотра отчета (JSON)"""
    sessions = scan_sessions()
    if sid not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_info = sessions[sid]
    
    # Получаем анализ сессии
    prepared = prepare_session(session_info, sample_rate=4.0)
    features = compute_basic_features(prepared["merged"])
    
    # Получаем информацию о пациентке
    patient_info = patient_manager.get_patient_info(
        session_info.folder_id, 
        session_info.group
    )
    
    # Генерируем заключение
    conclusion = report_generator._generate_conclusion(features, patient_info)
    
    return {
        "session_id": sid,
        "session_info": {
            "group": session_info.group,
            "folder_id": session_info.folder_id,
            "duration_seconds": features.get('duration_seconds'),
            "total_samples": features.get('total_samples')
        },
        "patient_info": {
            "age": patient_info.get("age"),
            "gestation_weeks": patient_info.get("gestation_weeks"),
            "diagnosis": patient_info.get("diagnosis"),
            "risk_factors": patient_info.get("risk_factors", {})
        },
        "analysis": {
            "bpm_statistics": {
                "mean": features.get('mean_bpm'),
                "median": features.get('median_bpm'),
                "max": features.get('max_bpm'),
                "min": features.get('min_bpm'),
                "std": features.get('std_bpm')
            },
            "events": {
                "decelerations": features.get('decel_count', 0),
                "tachycardia": features.get('tachy_count', 0),
                "bradycardia": features.get('brady_count', 0)
            }
        },
        "conclusion": conclusion
    }

# --------------------
# Запуск (локально, без Docker)
# --------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)