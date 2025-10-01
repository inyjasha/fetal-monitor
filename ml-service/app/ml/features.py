
import numpy as np
import pandas as pd

def detect_decelerations(bpm: np.ndarray, time: np.ndarray, drop_threshold=15, min_duration=10):
    """
    Возвращает список децелераций:
    - drop_threshold: сколько ударов в минуту упало от baseline
    - min_duration: минимальная длительность в секундах
    """
    decels = []
    baseline = pd.Series(bpm).rolling(window=60, min_periods=1).median().to_numpy()  # 1 минута
    below = bpm < (baseline - drop_threshold)
    start, end = None, None
    for i, val in enumerate(below):
        if val and start is None:
            start = time[i]
        elif not val and start is not None:
            end = time[i-1]
            if end - start >= min_duration:
                decels.append({"start": start, "end": end, "duration": end-start})
            start = None
    if start is not None:
        end = time[-1]
        if end - start >= min_duration:
            decels.append({"start": start, "end": end, "duration": end-start})
    return decels

def detect_tachycardia(bpm: np.ndarray, threshold=160):
    return np.where(bpm > threshold)[0]

def detect_bradycardia(bpm: np.ndarray, threshold=110):
    return np.where(bpm < threshold)[0]

def compute_variability(bpm: np.ndarray, window_sec=60, sample_rate=4):
    """
    STV: стандартное отклонение в скользящем окне
    """
    window_size = int(window_sec * sample_rate)
    return pd.Series(bpm).rolling(window=window_size, min_periods=1).std().to_numpy()
