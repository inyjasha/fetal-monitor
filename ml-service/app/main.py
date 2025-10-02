from datetime import datetime
import os
import sys
import asyncio
import logging
from typing import Dict, List, Optional, Any
import json
import tempfile
import numpy as np
import pandas as pd
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import os
from fastapi import UploadFile, File, Form
import uuid
from pathlib import Path

import zipfile
import shutil
from app.ml_metrics import simple_metrics

# ИМПОРТЫ ДЛЯ ML МЕТРИК
from sklearn.metrics import (
    accuracy_score, 
    precision_score, 
    recall_score, 
    f1_score, 
    classification_report, 
    confusion_matrix,
    roc_auc_score,
    mean_squared_error,
    mean_absolute_error,
    r2_score
)
from sklearn.preprocessing import label_binarize
import scipy.stats as stats

logger = logging.getLogger("simple-metrics")

bpm_history = []
prediction_history = []

# --------------------
# Настройка путей
# --------------------

# Определяем базовую директорию проекта
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # папка app
ML_SERVICE_DIR = os.path.dirname(BASE_DIR)  # папка ml-service
PROJECT_ROOT = os.path.dirname(ML_SERVICE_DIR)  # папка fetal-monitor

# Пути к фронтенду
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")

print(f"🔍 Поиск директорий:")
print(f"   BASE_DIR: {BASE_DIR}")
print(f"   ML_SERVICE_DIR: {ML_SERVICE_DIR}")
print(f"   PROJECT_ROOT: {PROJECT_ROOT}")
print(f"   FRONTEND_DIR: {FRONTEND_DIR}")
print(f"   STATIC_DIR: {STATIC_DIR}")
print(f"   TEMPLATES_DIR: {TEMPLATES_DIR}")

# Проверяем существование директорий
if os.path.exists(STATIC_DIR):
    print(f"✅ Найдена директория static: {STATIC_DIR}")
else:
    print(f"❌ Директория static не найдена: {STATIC_DIR}")

if os.path.exists(TEMPLATES_DIR):
    print(f"✅ Найдена директория templates: {TEMPLATES_DIR}")
else:
    print(f"❌ Директория templates не найдена: {TEMPLATES_DIR}")

# Добавляем пути в sys.path для импортов
sys.path.append(BASE_DIR)
sys.path.append(ML_SERVICE_DIR)

# Импорты остальных модулей (с обработкой ошибок)
try:
    from app.ml.patient_data import patient_manager
    print("✅ Модуль patient_data загружен")
except ImportError as e:
    print(f"⚠️ Не удалось импортировать patient_data: {e}")
    # Создаем заглушку
    class PatientManagerStub:
        def get_patient_info(self, *args, **kwargs):
            return {
                "age": 30,
                "gestation_weeks": 32,
                "diagnosis": "Неизвестно",
                "has_diabetes": False,
                "has_anemia": False,
                "has_hypertension": False,
                "risk_factors": {},
                "Ph": 7.4,
                "Glu": 5.0,
                "LAC": 1.0,
                "BE": 0.0,
                "CO2": 25.0
            }
    patient_manager = PatientManagerStub()

try:
    from app.ml.report_generator import report_generator
    print("✅ Модуль report_generator загружен")
except ImportError as e:
    print(f"⚠️ Не удалось импортировать report_generator: {e}")
    # Создаем заглушку
    class ReportGeneratorStub:
        def generate_session_report(self, *args, **kwargs):
            return "/tmp/report.pdf"
    report_generator = ReportGeneratorStub()

try:
    from app.auth import router as auth_router
    print("✅ Модуль auth загружен")
except ImportError as e:
    print(f"⚠️ Не удалось импортировать auth: {e}")
    # Создаем заглушку для роутера
    from fastapi import APIRouter
    auth_router = APIRouter()

# Импортируем функции из stream.py для работы с реальными данными
try:
    from app.stream import scan_sessions, prepare_session
    print("✅ Модуль stream загружен")
except ImportError as e:
    print(f"❌ Не удалось импортировать stream: {e}")
    raise ImportError("Модуль stream обязателен для работы с реальными данными")

try:
    from app.patients_search import router as patients_router
    print("✅ Модуль patients_search загружен")
except ImportError as e:
    print(f"⚠️ Не удалось импортировать patients_search: {e}")
    from fastapi import APIRouter
    patients_router = APIRouter()

# --------------------
# Логирование
# --------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ml-service")

# --------------------
# FastAPI app
# --------------------
app = FastAPI(title="Fetal Monitor ML Service")

# CORS (для фронтенда)
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтирование статических файлов и шаблонов
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    print(f"✅ Статические файлы подключены из: {STATIC_DIR}")
else:
    print(f"❌ Директория static не найдена")

if os.path.exists(TEMPLATES_DIR):
    templates = Jinja2Templates(directory=TEMPLATES_DIR)
    print(f"✅ Шаблоны подключены из: {TEMPLATES_DIR}")
else:
    print(f"❌ Директория templates не найдена")
    templates = None

# Подключение роутеров
try:
    app.include_router(auth_router)
    app.include_router(patients_router)
    print("✅ Роутеры успешно подключены")
except Exception as e:
    print(f"⚠️ Предупреждение: Не удалось подключить некоторые роутеры: {e}")

# --------------------
# Вспомогательные функции для анализа
# --------------------
def compute_basic_features(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Упрощенная версия вычисления признаков для анализа сессии.
    Использует реальные данные из stream.py
    """
    # Используем отфильтрованные данные если есть, иначе сырые
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
    """Простой предсказатель трендов на основе реальных данных"""
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

# --------------------
# REST endpoints
# --------------------
@app.get("/")
async def root(request: Request):
    if templates:
        return templates.TemplateResponse("main.html", {"request": request})
    else:
        return JSONResponse({"message": "Fetal Monitor ML Service", "status": "running", "templates": "not available"})

@app.get("/kgt-monitoring")
async def kgt_monitoring(request: Request):
    if templates:
        return templates.TemplateResponse("startKGT.html", {"request": request})
    else:
        return JSONResponse({"message": "KGT Monitoring", "status": "running", "templates": "not available"})

@app.get("/api/ping")
def ping():
    return {"msg": "pong", "status": "success"}

@app.get("/api/sessions")
def list_sessions():
    """Вернуть список доступных сессий из реальных данных"""
    try:
        sessions = scan_sessions()
        result = [
            {"session_id": sid, "group": info.group, "folder_id": info.folder_id}
            for sid, info in sessions.items()
        ]
        print(f"📋 Загружено сессий из реальных данных: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        return []

@app.get("/api/sessions/{sid}")
def session_info(sid: str, sample_rate: float = Query(4.0, description="Частота выборки, Гц")):
    """Метаданные по конкретной сессии из реальных данных"""
    try:
        sessions = scan_sessions()
        if sid not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        prepared = prepare_session(sessions[sid], sample_rate=sample_rate)
        return {
            "meta": prepared["meta"],
            "n_samples": len(prepared["merged"]),
            "warnings": prepared["warnings"],
        }
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{sid}/analysis")
def session_analysis(sid: str, sample_rate: float = Query(4.0)):
    """Анализ сессии с учетом данных пациентки из реальных данных"""
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

@app.get("/api/sessions/{sid}/patient-info")
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

# --------------------
# WebSocket streaming с предсказаниями из реальных данных
# --------------------
@app.websocket("/ws/stream/{sid}")
async def websocket_stream(websocket: WebSocket, sid: str, sample_rate: float = 4.0):
    """
    Стрим РЕАЛЬНЫХ данных с предсказаниями из CSV файлов через stream.py
    """
    await websocket.accept()
    sessions = scan_sessions()

    if sid not in sessions:
        await websocket.send_json({"error": f"Session {sid} not found"})
        await websocket.close()
        return

    # Загружаем реальные данные через stream.py
    prepared = prepare_session(sessions[sid], sample_rate=sample_rate)
    merged = prepared["merged"]

    # Логируем информацию о реальных данных
    print(f"📊 Загружено реальных данных: {len(merged)} строк")
    print(f"📊 Колонки: {merged.columns.tolist()}")
    
    if not merged.empty:
        bpm_data = merged.get("bpm", merged.get("bpm_filtered"))
        if bpm_data is not None:
            bpm_valid = bpm_data.dropna()
            print(f"📊 Статистика ЧСС: samples={len(bpm_valid)}, min={bpm_valid.min()}, max={bpm_valid.max()}, mean={bpm_valid.mean():.1f}")
        
        uterus_data = merged.get("uterus", merged.get("uterus_filtered"))
        if uterus_data is not None:
            uterus_valid = uterus_data.dropna()
            print(f"📊 Статистика сокращений: samples={len(uterus_valid)}, min={uterus_valid.min()}, max={uterus_valid.max()}, mean={uterus_valid.mean():.1f}")

    # Инициализируем предсказатели
    trend_predictor = SimpleTrendPredictor(window_size=100)
    risk_predictor = RiskPredictor()
    
    # ИНИЦИАЛИЗИРУЕМ ВСЕ БУФЕРЫ - ДОБАВЬТЕ ЭТО
    bpm_buffer = []  # ДЛЯ ПРЕДСКАЗАТЕЛЕЙ
    bpm_history = []  # ДЛЯ МЕТРИК
    prediction_history = []  # ДЛЯ МЕТРИК
    
    # Буфер для анализа
    prediction_interval = 2.0  # секунды между предсказаниями
    last_prediction_time = 0.0

    # Отправляем метаданные в начале
    await websocket.send_json({
        "type": "meta",
        "meta": prepared["meta"], 
        "warnings": prepared["warnings"],
        "data_info": {
            "total_samples": len(merged),
            "columns": merged.columns.tolist(),
            "sample_rate": sample_rate,
            "has_real_data": True
        }
    })

    step = 1.0 / sample_rate
    
    try:
        for index, row in merged.iterrows():
            current_time = float(row["time"])
            
            # Получаем РЕАЛЬНЫЕ данные из CSV
            bpm_val = None
            if 'bpm' in row and not pd.isna(row['bpm']):
                bpm_val = float(row['bpm'])
            elif 'bpm_filtered' in row and not pd.isna(row['bpm_filtered']):
                bpm_val = float(row['bpm_filtered'])
            
            uterus_val = None
            if 'uterus' in row and not pd.isna(row['uterus']):
                uterus_val = float(row['uterus'])
            elif 'uterus_filtered' in row and not pd.isna(row['uterus_filtered']):
                uterus_val = float(row['uterus_filtered'])
            
            # Основной фрейм данных
            payload = {
                "type": "frame",
                "time": current_time,
                "bpm": bpm_val,
                "uterus": uterus_val,
                "index": index
            }
            await websocket.send_json(payload)

            # ОБРАБОТКА МЕТРИК
            if bpm_val is not None:
                bpm_history.append(bpm_val)
                
                # Ограничиваем размер истории
                if len(bpm_history) > 1000:
                    bpm_history.pop(0)
                
                # Выводим метрики каждые 100 точек
                if len(bpm_history) % 100 == 0:
                    print(f"\n🔄 Получено {len(bpm_history)} точек данных...")
                    simple_metrics.calculate_and_print_metrics(bpm_history, prediction_history)

            # Обновляем предсказатели
            if bpm_val is not None:
                trend_predictor.update(current_time, bpm_val)
                bpm_buffer.append(bpm_val)  # ТЕПЕРЬ bpm_buffer ИНИЦИАЛИЗИРОВАН
                # Ограничиваем размер буфера
                if len(bpm_buffer) > 200:
                    bpm_buffer.pop(0)

            # Отправляем предсказания каждые 2 секунды
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
                    "samples_in_buffer": len(bpm_buffer),
                    "bpm_std": float(np.std(bpm_buffer)) if len(bpm_buffer) > 1 else 0.0
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
                
                # ОБРАБОТКА ПРЕДСКАЗАНИЙ ДЛЯ МЕТРИК
                prediction_history.append(prediction_packet)
                if len(prediction_history) > 200:
                    prediction_history.pop(0)
                
                last_prediction_time = current_time

            await asyncio.sleep(step)

    except WebSocketDisconnect:
        logger.info(f"Клиент отключился от {sid}")
    except Exception as e:
        logger.error(f"Ошибка в WebSocket потоке: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})

# --------------------
# Новые endpoint'ы для выбора сессии
# --------------------
@app.get("/api/available-sessions")
async def get_available_sessions():
    """Получить список доступных сессий с группировкой из реальных данных"""
    try:
        sessions = scan_sessions()
        print(f"🔍 Найдено сессий из реальных данных: {len(sessions)}")
        
        # Группируем сессии по типу и папке
        grouped_sessions = {}
        
        for session_id, session_info in sessions.items():
            group = getattr(session_info, 'group', 'unknown')
            folder_id = getattr(session_info, 'folder_id', 'unknown')
            
            group_key = f"{group}_{folder_id}"
            if group_key not in grouped_sessions:
                grouped_sessions[group_key] = {
                    "group": group,
                    "folder_id": folder_id,
                    "sessions": []
                }
            grouped_sessions[group_key]["sessions"].append({
                "session_id": session_id,
                "duration": "30 минут"  # Можно вычислить из реальных данных
            })
        
        result = list(grouped_sessions.values())
        print(f"📊 Сгруппированные сессии: {len(result)} групп")
        return result
        
    except Exception as e:
        logger.error(f"Error getting available sessions: {e}")
        return [{"group": "regular", "folder_id": "1", "sessions": [{"session_id": "1", "duration": "30 минут"}]}]

@app.post("/api/select-session")
async def select_session(request: Request):
    """Выбрать сессию для мониторинга"""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID is required")
        
        sessions = scan_sessions()
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        logger.error(f"Error selecting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Хранилище загруженных сессий в памяти
uploaded_sessions = {}

@app.get("/api/uploaded-sessions")
def list_uploaded_sessions():
    """Список загруженных сессий"""
    return list(uploaded_sessions.values())

@app.post("/api/upload-kgt")
async def upload_kgt(
    file: UploadFile = File(...),
    patient_name: str = Form("Неизвестный пациент"),
    session_duration: str = Form("30 минут")
):
    """Загрузка КГТ файла с компьютера"""
    try:
        # Создаем временную директорию для распаковки
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Сохраняем загруженный файл
            file_path = temp_path / file.filename
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            # Проверяем, является ли файл архивом
            if file.filename.endswith('.zip'):
                # Распаковываем архив
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # Ищем CSV файлы в распакованных файлах
                csv_files = list(temp_path.glob("**/*.csv"))
                if not csv_files:
                    raise HTTPException(status_code=400, detail="В архиве не найдены CSV файлы")
                
                # Берем первый найденный CSV файл
                data_file = csv_files[0]
            else:
                data_file = file_path
            
            # Читаем данные из CSV файла
            df = pd.read_csv(data_file)
            
            # Проверяем необходимые колонки
            required_columns = ['time', 'bpm']
            if not all(col in df.columns for col in required_columns):
                raise HTTPException(
                    status_code=400, 
                    detail=f"CSV файл должен содержать колонки: {required_columns}"
                )
            
            # Обрабатываем данные
            processed_data = process_uploaded_kgt_data(df)
            
            # Генерируем уникальный ID для сессии
            session_id = str(uuid.uuid4())
            
            # Сохраняем сессию в памяти (в реальном приложении - в базе данных)
            uploaded_sessions[session_id] = {
                "session_id": session_id,
                "patient_name": patient_name,
                "session_duration": session_duration,
                "upload_time": datetime.now().isoformat(),
                "data": processed_data,
                "original_filename": file.filename,
                "data_points": len(processed_data)
            }
            
            return {
                "status": "success",
                "session_id": session_id,
                "patient_name": patient_name,
                "data_points": len(processed_data),
                "duration_seconds": len(processed_data) / 4.0  # Предполагаем 4 Гц
            }
            
    except Exception as e:
        logger.error(f"Error uploading KGT file: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")

def process_uploaded_kgt_data(df: pd.DataFrame) -> List[Dict]:
    """Обработка загруженных данных КГТ"""
    processed_data = []
    
    for index, row in df.iterrows():
        data_point = {
            "time": float(row.get("time", index / 4.0)),  # По умолчанию 4 Гц
            "bpm": float(row.get("bpm", 0)),
            "uterus": float(row.get("uterus", row.get("contractions", 0))),
            "index": index
        }
        processed_data.append(data_point)
    
    return processed_data

# Хранилище загруженных сессий в памяти
uploaded_sessions = {}

@app.get("/api/uploaded-sessions")
def list_uploaded_sessions():
    """Список загруженных сессий"""
    return list(uploaded_sessions.values())

@app.websocket("/ws/stream/uploaded/{session_id}")
async def websocket_stream_uploaded(websocket: WebSocket, session_id: str, sample_rate: float = 4.0):
    """Стрим загруженных данных КГТ из папки"""
    await websocket.accept()
    
    if session_id not in uploaded_sessions:
        await websocket.send_json({"error": f"Uploaded session {session_id} not found"})
        await websocket.close()
        return
    
    session_data = uploaded_sessions[session_id]
    
    try:
        # Используем подготовленные данные через stream.py
        prepared = session_data["prepared_data"]
        merged = prepared["merged"]
        
        logger.info(f"Начало стрима загруженной сессии: {len(merged)} точек данных")
        
        # Инициализируем предсказатели
        trend_predictor = SimpleTrendPredictor(window_size=100)
        risk_predictor = RiskPredictor()
        
        # ИНИЦИАЛИЗИРУЕМ ВСЕ БУФЕРЫ
        bpm_buffer = []  # ДЛЯ ПРЕДСКАЗАТЕЛЕЙ
        bpm_history = []  # ДЛЯ МЕТРИК
        prediction_history = []  # ДЛЯ МЕТРИК
        
        # Буфер для анализа
        prediction_interval = 2.0
        last_prediction_time = 0.0
        
        # Отправляем метаданные
        await websocket.send_json({
            "type": "meta",
            "meta": {
                "patient_name": session_data["patient_name"],
                "session_duration": f"{len(merged) / 4.0 / 60:.1f} минут",
                "data_points": len(merged),
                "source": "folder_upload",
                "original_filename": session_data.get("original_filename", "Unknown")
            },
            "data_info": {
                "total_samples": len(merged),
                "sample_rate": sample_rate,
                "has_real_data": True
            }
        })
        
        step = 1.0 / sample_rate
        
        for index, row in merged.iterrows():
            current_time = float(row["time"])
            
            # Получаем данные из подготовленного DataFrame
            bpm_val = None
            if 'bpm_filtered' in row and not pd.isna(row['bpm_filtered']):
                bpm_val = float(row['bpm_filtered'])
            elif 'bpm' in row and not pd.isna(row['bpm']):
                bpm_val = float(row['bpm'])
            
            uterus_val = None
            if 'uterus_filtered' in row and not pd.isna(row['uterus_filtered']):
                uterus_val = float(row['uterus_filtered'])
            elif 'uterus' in row and not pd.isna(row['uterus']):
                uterus_val = float(row['uterus'])
            
            # Основной фрейм данных
            payload = {
                "type": "frame",
                "time": current_time,
                "bpm": bpm_val,
                "uterus": uterus_val,
                "index": index
            }
            await websocket.send_json(payload)
            
            # ОБРАБОТКА МЕТРИК
            if bpm_val is not None:
                bpm_history.append(bpm_val)
                
                if len(bpm_history) > 1000:
                    bpm_history.pop(0)
                
                if len(bpm_history) % 100 == 0:
                    print(f"\n🔄 Получено {len(bpm_history)} точек данных...")
                    simple_metrics.calculate_and_print_metrics(bpm_history, prediction_history)
            
            # Обновляем предсказатели
            if bpm_val is not None:
                trend_predictor.update(current_time, bpm_val)
                bpm_buffer.append(bpm_val)  # ТЕПЕРЬ bpm_buffer ИНИЦИАЛИЗИРОВАН
                if len(bpm_buffer) > 200:
                    bpm_buffer.pop(0)
            
            # Отправляем предсказания
            if current_time - last_prediction_time >= prediction_interval and len(bpm_buffer) >= 10:
                trend_pred = trend_predictor.predict_trend()
                risk_pred = risk_predictor.predict_risk(bpm_buffer)
                
                current_stats = {
                    "mean_bpm_1min": float(np.mean(bpm_buffer[-60:])) if len(bpm_buffer) >= 60 else float(np.mean(bpm_buffer)),
                    "median_bpm_1min": float(np.median(bpm_buffer[-60:])) if len(bpm_buffer) >= 60 else float(np.median(bpm_buffer)),
                    "current_bpm": bpm_val,
                    "samples_in_buffer": len(bpm_buffer),
                    "bpm_std": float(np.std(bpm_buffer)) if len(bpm_buffer) > 1 else 0.0
                }
                
                prediction_packet = {
                    "type": "prediction",
                    "timestamp": current_time,
                    "trend": trend_pred,
                    "risk": risk_pred,
                    "statistics": current_stats
                }
                await websocket.send_json(prediction_packet)
                
                # ОБРАБОТКА ПРЕДСКАЗАНИЙ ДЛЯ МЕТРИК
                prediction_history.append(prediction_packet)
                if len(prediction_history) > 200:
                    prediction_history.pop(0)
                
                last_prediction_time = current_time
            
            await asyncio.sleep(step)
            
    except WebSocketDisconnect:
        logger.info(f"Клиент отключился от uploaded session {session_id}")
    except Exception as e:
        logger.error(f"Ошибка в WebSocket потоке загруженных данных: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})

@app.post("/api/upload-kgt-zip")
async def upload_kgt_zip(
    file: UploadFile = File(...),
    patient_name: str = Form("Неизвестный пациент")
):
    """Загрузка КГТ данных из ZIP архива с папками bpm и uterus"""
    try:
        # Проверяем, что файл является ZIP архивом
        if not file.filename.lower().endswith('.zip'):
            raise HTTPException(status_code=400, detail="Файл должен быть ZIP архивом")
        
        # Создаем временную директорию для распаковки
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Сохраняем загруженный ZIP файл
            zip_path = temp_path / file.filename
            with open(zip_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            
            logger.info(f"ZIP файл сохранен: {zip_path}")
            
            # Распаковываем архив
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path)
            
            logger.info(f"ZIP архив распакован в: {temp_path}")
            
            # Ищем папки bpm и uterus в распакованной структуре
            bpm_files = []
            uterus_files = []
            
            # Ищем все CSV файлы в папках bpm и uterus
            for csv_file in temp_path.glob("**/bpm/*.csv"):
                bpm_files.append(str(csv_file))
                logger.info(f"Найден BPM файл: {csv_file}")
            
            for csv_file in temp_path.glob("**/uterus/*.csv"):
                uterus_files.append(str(csv_file))
                logger.info(f"Найден Uterus файл: {csv_file}")
            
            # Альтернативный поиск - если папки находятся в корне
            if not bpm_files:
                bpm_dir = temp_path / "bpm"
                if bpm_dir.exists():
                    for csv_file in bpm_dir.glob("*.csv"):
                        bpm_files.append(str(csv_file))
                        logger.info(f"Найден BPM файл (в корне): {csv_file}")
            
            if not uterus_files:
                uterus_dir = temp_path / "uterus"
                if uterus_dir.exists():
                    for csv_file in uterus_dir.glob("*.csv"):
                        uterus_files.append(str(csv_file))
                        logger.info(f"Найден Uterus файл (в корне): {csv_file}")
            
            if not bpm_files and not uterus_files:
                # Показываем структуру архива для отладки
                archive_structure = []
                for item in temp_path.rglob("*"):
                    if item.is_file():
                        archive_structure.append(str(item.relative_to(temp_path)))
                
                logger.error(f"В архиве не найдены CSV файлы в папках bpm/uterus. Структура архива: {archive_structure}")
                raise HTTPException(
                    status_code=400, 
                    detail="В архиве не найдены CSV файлы в папках bpm и uterus. Архив должен содержать папки 'bpm' и 'uterus' с CSV файлами."
                )
            
            # Создаем SessionInfo для обработки через stream.py
            session_info = create_session_from_files(bpm_files, uterus_files, patient_name)
            
            if not session_info:
                raise HTTPException(status_code=400, detail="Не удалось создать сессию из файлов")
            
            # Подготавливаем сессию через stream.py
            prepared = prepare_session(session_info, sample_rate=4.0)
            
            # Генерируем уникальный ID для сессии
            session_id = str(uuid.uuid4())
            
            # Сохраняем сессию в памяти
            uploaded_sessions[session_id] = {
                "session_id": session_id,
                "patient_name": patient_name,
                "session_info": session_info,
                "prepared_data": prepared,
                "upload_time": datetime.now().isoformat(),
                "data_points": len(prepared["merged"]),
                "source": "zip_upload",
                "original_filename": file.filename
            }
            
            logger.info(f"Успешно загружен ZIP архив: {file.filename}, {len(prepared['merged'])} точек данных")
            
            return {
                "status": "success",
                "session_id": session_id,
                "patient_name": patient_name,
                "data_points": len(prepared["merged"]),
                "duration_seconds": len(prepared["merged"]) / 4.0,
                "meta": prepared["meta"]
            }
            
    except zipfile.BadZipFile:
        logger.error(f"Некорректный ZIP файл: {file.filename}")
        raise HTTPException(status_code=400, detail="Некорректный ZIP файл")
    except Exception as e:
        logger.error(f"Error uploading KGT ZIP: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка обработки ZIP архива: {str(e)}")

def create_session_from_files(bpm_files: List[str], uterus_files: List[str], patient_name: str):
    """Создает SessionInfo из списков файлов для обработки через stream.py"""
    
    if not bpm_files and not uterus_files:
        return None
    
    # Импортируем SessionInfo из stream.py
    try:
        from app.stream import SessionInfo
    except ImportError as e:
        logger.error(f"Не удалось импортировать SessionInfo: {e}")
        return None
    
    # Создаем SessionInfo
    session_info = SessionInfo(
        group="uploaded",  # специальная группа для загруженных данных
        folder_id=patient_name.replace(" ", "_"),
        session_id=f"uploaded_{int(datetime.now().timestamp())}",
        bpm_files=sorted(bpm_files),
        uterus_files=sorted(uterus_files)
    )
    
    logger.info(f"Создана сессия из файлов: {len(bpm_files)} BPM файлов, {len(uterus_files)} uterus файлов")
    
    return session_info

def create_session_from_folder(folder_path: Path, patient_name: str):
    """Создает SessionInfo из структуры папки для обработки через stream.py"""
    
    bpm_dir = folder_path / "bpm"
    uterus_dir = folder_path / "uterus"
    
    bpm_files = []
    uterus_files = []
    
    # Собираем BPM файлы
    if bpm_dir.exists():
        for csv_file in bpm_dir.glob("*.csv"):
            bpm_files.append(str(csv_file))
    
    # Собираем Uterus файлы
    if uterus_dir.exists():
        for csv_file in uterus_dir.glob("*.csv"):
            uterus_files.append(str(csv_file))
    
    if not bpm_files and not uterus_files:
        return None
    
    # Импортируем SessionInfo из stream.py
    try:
        from app.stream import SessionInfo
    except ImportError as e:
        logger.error(f"Не удалось импортировать SessionInfo: {e}")
        return None
    
    # Создаем SessionInfo
    session_info = SessionInfo(
        group="uploaded",  # специальная группа для загруженных данных
        folder_id=patient_name.replace(" ", "_"),
        session_id=f"uploaded_{int(datetime.now().timestamp())}",
        bpm_files=sorted(bpm_files),
        uterus_files=sorted(uterus_files)
    )
    
    logger.info(f"Создана сессия: {len(bpm_files)} BPM файлов, {len(uterus_files)} uterus файлов")
    
    return session_info

# WebSocket для загруженных папок (использует ту же логику)
@app.websocket("/ws/stream/uploaded/{session_id}")
async def websocket_stream_uploaded(websocket: WebSocket, session_id: str, sample_rate: float = 4.0):
    """Стрим загруженных данных КГТ из папки"""
    await websocket.accept()
    
    if session_id not in uploaded_sessions:
        await websocket.send_json({"error": f"Uploaded session {session_id} not found"})
        await websocket.close()
        return
    
    session_data = uploaded_sessions[session_id]
    prepared = session_data["prepared_data"]
    merged = prepared["merged"]
    
    # Инициализируем предсказатели
    trend_predictor = SimpleTrendPredictor(window_size=100)
    risk_predictor = RiskPredictor()
    
    # Буфер для анализа
    bpm_buffer = []
    prediction_interval = 2.0
    last_prediction_time = 0.0
    
    # Отправляем метаданные
    await websocket.send_json({
        "type": "meta",
        "meta": {
            "patient_name": session_data["patient_name"],
            "session_duration": f"{len(merged) / 4.0 / 60:.1f} минут",
            "data_points": len(merged),
            "source": "folder_upload",
            "folder_path": session_data.get("folder_path", "Unknown")
        },
        "data_info": {
            "total_samples": len(merged),
            "sample_rate": sample_rate,
            "has_real_data": True
        }
    })
    
    step = 1.0 / sample_rate
    
    try:
        for index, row in merged.iterrows():
            current_time = float(row["time"])
            
            # Получаем данные из подготовленного DataFrame
            bpm_val = None
            if 'bpm' in row and not pd.isna(row['bpm']):
                bpm_val = float(row['bpm'])
            elif 'bpm_filtered' in row and not pd.isna(row['bpm_filtered']):
                bpm_val = float(row['bpm_filtered'])
            
            uterus_val = None
            if 'uterus' in row and not pd.isna(row['uterus']):
                uterus_val = float(row['uterus'])
            elif 'uterus_filtered' in row and not pd.isna(row['uterus_filtered']):
                uterus_val = float(row['uterus_filtered'])
            
            # Основной фрейм данных
            payload = {
                "type": "frame",
                "time": current_time,
                "bpm": bpm_val,
                "uterus": uterus_val,
                "index": index
            }
            await websocket.send_json(payload)
            
            # Обновляем предсказатели
            if bpm_val is not None:
                trend_predictor.update(current_time, bpm_val)
                bpm_buffer.append(bpm_val)
                if len(bpm_buffer) > 200:
                    bpm_buffer.pop(0)
            
            # Отправляем предсказания
            if current_time - last_prediction_time >= prediction_interval and len(bpm_buffer) >= 10:
                trend_pred = trend_predictor.predict_trend()
                risk_pred = risk_predictor.predict_risk(bpm_buffer)
                
                current_stats = {
                    "mean_bpm_1min": float(np.mean(bpm_buffer[-60:])) if len(bpm_buffer) >= 60 else float(np.mean(bpm_buffer)),
                    "median_bpm_1min": float(np.median(bpm_buffer[-60:])) if len(bpm_buffer) >= 60 else float(np.median(bpm_buffer)),
                    "current_bpm": bpm_val,
                    "samples_in_buffer": len(bpm_buffer),
                    "bpm_std": float(np.std(bpm_buffer)) if len(bpm_buffer) > 1 else 0.0
                }
                
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
        logger.info(f"Клиент отключился от uploaded session {session_id}")
    except Exception as e:
        logger.error(f"Ошибка в WebSocket потоке загруженных данных: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})


@app.get("/api/metrics/ml-detailed")
async def get_ml_detailed_metrics():
    """Получить детальные ML метрики"""
    try:
        if not bpm_history:
            return {"message": "Нет данных для расчета метрик"}
        
        bpm_array = np.array([x for x in bpm_history if x is not None])
        
        if len(bpm_array) == 0:
            return {"message": "Нет валидных данных BPM"}
        
        # Генерация тестовых данных
        y_true, y_pred, y_pred_proba = simple_metrics._generate_test_predictions(bpm_array, prediction_history)
        
        # Расчет всех метрик
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_true, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
        
        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        cm_percentage = (cm / cm.sum(axis=1, keepdims=True) * 100).round(1)
        
        # Classification report
        class_report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
        
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "basic_metrics": {
                "accuracy": float(accuracy),
                "precision": float(precision),
                "recall": float(recall),
                "f1_score": float(f1),
                "samples_count": len(y_true),
                "classes_count": len(np.unique(y_true))
            },
            "confusion_matrix": {
                "matrix": cm.tolist(),
                "percentage": cm_percentage.tolist(),
                "labels": ["Норма", "Тахикардия", "Брадикардия"]
            },
            "class_report": class_report,
            "data_quality": {
                "total_samples": len(bpm_history),
                "valid_samples": len(bpm_array),
                "completeness": len(bpm_array) / len(bpm_history) * 100
            }
        }
        
        # Вывод в терминал
        print(f"\n🎯 ДЕТАЛЬНЫЕ ML МЕТРИКИ:")
        print(f"   Accuracy: {accuracy:.3f}")
        print(f"   Precision: {precision:.3f}")
        print(f"   Recall: {recall:.3f}")
        print(f"   F1-Score: {f1:.3f}")
        print(f"   Confusion Matrix:")
        print(f"   {cm}")
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating detailed ML metrics: {e}")
        return {"error": str(e)}
# --------------------
# Запуск
# --------------------
if __name__ == "__main__":
    import uvicorn
    print("🚀 Запуск сервера на http://localhost:8001")
    print("📊 Используются РЕАЛЬНЫЕ данные из CSV файлов через stream.py")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)