# ml/predict.py
import numpy as np
from .features import detect_decelerations, detect_tachycardia, detect_bradycardia, compute_variability
from .models import load_risk_model

def compute_session_features(merged_df):
    bpm = merged_df["bpm_filtered"].to_numpy()
    time = merged_df["time"].to_numpy()
    
    decels = detect_decelerations(bpm, time)
    tachy = detect_tachycardia(bpm)
    brady = detect_bradycardia(bpm)
    stv = compute_variability(bpm)
    
    return {
        "decelerations": decels,
        "tachy_indices": tachy.tolist(),
        "brady_indices": brady.tolist(),
        "short_term_variability": stv.tolist()
    }

def predict_risk(features: dict):
    model = load_risk_model()
    # преобразуем фичи в вектор для модели (пример)
    X = [
        len(features["decelerations"]),
        len(features["tachy_indices"]),
        len(features["brady_indices"]),
        np.mean(features["short_term_variability"])
    ]
    risk = model.predict([X])[0]
    return {"risk": int(risk)}
