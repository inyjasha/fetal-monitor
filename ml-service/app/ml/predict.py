# ml/predict.py
"""
Функции для вычисления признаков с учетом данных пациенток.
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

from .features import detect_decelerations, detect_tachycardia, detect_bradycardia, compute_variability
from .patient_data import patient_manager

def safe_mean(arr):
    arr = np.array(arr, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) == 0:
        return None
    return float(np.mean(arr))

def compute_features_from_buffer(times: np.ndarray, bpm: np.ndarray, uterus: np.ndarray,
                                 patient_info: Optional[Dict[str, Any]] = None, 
                                 session_meta: Optional[Dict[str, Any]] = None,
                                 sample_rate: float = 4.0) -> Dict[str, Any]:
    """
    УЛУЧШЕННАЯ версия: вычисляет признаки с учетом данных пациентки.
    """
    # Если patient_info не предоставлен, но есть session_meta, загружаем данные пациентки
    if patient_info is None and session_meta is not None:
        folder_id = session_meta.get('folder_id')
        group = session_meta.get('group')
        if folder_id and group:
            patient_info = patient_manager.get_patient_info(folder_id, group)
    
    patient_info = patient_info or {}
    
    # clean arrays
    if len(times) == 0:
        return {}

    # выбираем маску валидных bpm
    bpm_valid_mask = ~np.isnan(bpm)
    if bpm_valid_mask.any():
        bpm_vals = bpm[bpm_valid_mask]
        bpm_times = times[bpm_valid_mask]
    else:
        bpm_vals = np.array([])
        bpm_times = np.array([])

    # decelerations — используем detect_decelerations (требует bpm и time)
    decels = detect_decelerations(bpm_vals, bpm_times) if len(bpm_vals) > 0 else []

    tachy_idx = detect_tachycardia(bpm_vals) if len(bpm_vals) > 0 else np.array([], dtype=int)
    brady_idx = detect_bradycardia(bpm_vals) if len(bpm_vals) > 0 else np.array([], dtype=int)

    stv = compute_variability(bpm_vals, window_sec=60, sample_rate=sample_rate) if len(bpm_vals) > 0 else np.array([])

    # Базовые фичи сигнала
    features = {
        # counts
        "decel_count": len(decels),
        "tachy_count": int(len(tachy_idx)),
        "brady_count": int(len(brady_idx)),
        # variability
        "stv_mean": safe_mean(stv),
        "stv_max": float(np.max(stv)) if len(stv) > 0 else None,
        "stv_min": float(np.min(stv)) if len(stv) > 0 else None,
        # last values
        "last_bpm": float(bpm_vals[-1]) if len(bpm_vals) > 0 else None,
        "last_uterus": float(uterus[~np.isnan(uterus)][-1]) if np.any(~np.isnan(uterus)) else None,
    }

    # Медицинские данные пациентки
    medical_features = {
        # Демографические данные
        "age": patient_info.get("age"),
        "gestation_weeks": patient_info.get("gestation_weeks"),
        
        # Газы крови
        "Ph": patient_info.get("Ph"),
        "CO2": patient_info.get("CO2"),
        "Glu": patient_info.get("Glu"),
        "LAC": patient_info.get("LAC"),
        "BE": patient_info.get("BE"),
        
        # Факторы риска
        "has_diabetes": patient_info.get("has_diabetes", False),
        "has_anemia": patient_info.get("has_anemia", False),
        "has_hypertension": patient_info.get("has_hypertension", False),
        
        # Композитные медицинские показатели
        "metabolic_acidosis": _check_metabolic_acidosis(patient_info),
        "respiratory_acidosis": _check_respiratory_acidosis(patient_info),
        "lactic_acidosis": _check_lactic_acidosis(patient_info),
    }
    
    features.update(medical_features)

    # добавим простую оценку тренда bpm
    try:
        if len(bpm_vals) >= 5:
            X = bpm_times.reshape(-1, 1)
            X0 = X - X.mean()
            coef = np.linalg.lstsq(X0, bpm_vals, rcond=None)[0][0]
            features["bpm_trend_slope"] = float(coef)
        else:
            features["bpm_trend_slope"] = None
    except Exception:
        features["bpm_trend_slope"] = None

    # компактный summary
    features["decelerations"] = decels
    features["tachy_indices"] = (bpm_times[tachy_idx].tolist() if len(tachy_idx) > 0 else [])
    features["brady_indices"] = (bpm_times[brady_idx].tolist() if len(brady_idx) > 0 else [])
    
    # Факторы риска как отдельный словарь
    features["risk_factors"] = patient_info.get("risk_factors", {})

    return features

def _check_metabolic_acidosis(patient_info: Dict[str, Any]) -> bool:
    """Проверяет метаболический ацидоз"""
    ph = patient_info.get("Ph")
    be = patient_info.get("BE")
    
    if ph is None or be is None:
        return False
    
    return ph < 7.35 and be < -2.0

def _check_respiratory_acidosis(patient_info: Dict[str, Any]) -> bool:
    """Проверяет респираторный ацидоз"""
    ph = patient_info.get("Ph")
    co2 = patient_info.get("CO2")
    
    if ph is None or co2 is None:
        return False
    
    return ph < 7.35 and co2 > 45.0

def _check_lactic_acidosis(patient_info: Dict[str, Any]) -> bool:
    """Проверяет лактат-ацидоз"""
    lac = patient_info.get("LAC")
    return lac is not None and lac > 4.0

def compute_session_features(merged_df: pd.DataFrame, session_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Офлайн полная сессия с учетом данных пациентки.
    """
    bpm = merged_df.get("bpm_filtered", merged_df.get("bpm")).to_numpy()
    time = merged_df["time"].to_numpy()
    uterus = merged_df.get("uterus_filtered", merged_df.get("uterus")).to_numpy() if "uterus" in merged_df else np.array([])

    return compute_features_from_buffer(time, bpm, uterus, session_meta=session_meta)