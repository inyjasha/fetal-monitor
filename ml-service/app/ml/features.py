# app/ml/features.py
import numpy as np
import pandas as pd

def detect_decelerations(bpm: np.ndarray, time: np.ndarray, drop_threshold: float = 15.0, min_duration: float = 10.0):
    if len(bpm) == 0:
        return []
    # baseline как медиана за 60 сек (если есть достаточное количество точек)
    window = max(1, int(60.0 * 4.0))
    baseline = pd.Series(bpm).rolling(window=window, min_periods=1, center=True).median().to_numpy()
    below = bpm < (baseline - drop_threshold)
    decels = []
    start_idx = None
    for i, val in enumerate(below):
        if val and start_idx is None:
            start_idx = i
        elif not val and start_idx is not None:
            # завершение
            start_t = time[start_idx]
            end_t = time[i-1]
            if (end_t - start_t) >= min_duration:
                decels.append({"start": float(start_t), "end": float(end_t), "duration": float(end_t-start_t)})
            start_idx = None
    if start_idx is not None:
        start_t = time[start_idx]
        end_t = time[-1]
        if (end_t - start_t) >= min_duration:
            decels.append({"start": float(start_t), "end": float(end_t), "duration": float(end_t-start_t)})
    return decels

def detect_tachycardia(bpm: np.ndarray, threshold: float = 160.0):
    if len(bpm) == 0:
        return np.array([], dtype=int)
    return np.where(bpm > threshold)[0]

def detect_bradycardia(bpm: np.ndarray, threshold: float = 110.0):
    if len(bpm) == 0:
        return np.array([], dtype=int)
    return np.where(bpm < threshold)[0]

def compute_variability(bpm: np.ndarray, window_sec: int = 60, sample_rate: int = 4):
    if len(bpm) == 0:
        return np.array([])
    window_size = max(1, int(window_sec * sample_rate))
    return pd.Series(bpm).rolling(window=window_size, min_periods=1).std().to_numpy()
