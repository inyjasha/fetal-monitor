# app/ml/online.py
"""
Online predictor — комплекс логики для потоковой обработки:
 - OnlineSessionState хранит буфер (time, bpm, uterus) и patient_info
 - ShortTermForecaster делает прогноз тренда на горизонты (5/10 минут)
 - OnlinePredictor собирает фичи и применяет долгосрочную модель (сквозная модель рисков)
"""

from typing import List, Dict, Optional, Any
import numpy as np
import time
import math
from dataclasses import dataclass, field
from collections import deque

from sklearn.linear_model import LinearRegression
from sklearn.exceptions import NotFittedError

from .predict import compute_features_from_buffer
from .models import load_risk_model  # долгосрочная обученная модель (joblib)

# --------------------
# Short-term forecaster
# --------------------
class ShortTermForecaster:
    """
    Предсказывает значение сигнала через horizon_sec на базе последних N секунд.
    Использует регуляризованную линейную регрессию на времени (можно заменить AR/SGD).
    Возвращает предсказание и оценку ошибки (RMSE на тренировочной выборке).
    """
    def __init__(self, window_sec: int = 300, sample_rate: float = 4.0, min_points: int = 30):
        self.window_size = int(window_sec * sample_rate)
        self.sample_rate = sample_rate
        self.times = deque(maxlen=self.window_size)
        self.values = deque(maxlen=self.window_size)
        self.model = LinearRegression()
        self._fitted = False

    def update(self, t: float, value: Optional[float]):
        if value is None or math.isnan(value) or math.isinf(value):
            return
        self.times.append(t)
        self.values.append(float(value))
        self._fitted = False  # надо переобучить модель перед прогнозом

    def _fit(self):
        if len(self.values) < 10:
            return
        X = np.array(self.times).reshape(-1, 1)
        y = np.array(self.values)
        # центрируем время для стабильности чисел
        X0 = X - X.mean()
        self.model.fit(X0, y)
        # сохраняем mean для предсказаний
        self._t_mean = float(X.mean())
        # оценка RMSE на обучающем наборе
        preds = self.model.predict(X0)
        self._rmse = float(np.sqrt(np.mean((preds - y) ** 2)))
        self._fitted = True

    def forecast(self, horizon_sec: float):
        if len(self.values) < 10:
            return {"pred": None, "rmse": None, "n": len(self.values)}
        if not self._fitted:
            self._fit()
        if not self._fitted:
            return {"pred": None, "rmse": None, "n": len(self.values)}
        t_last = float(self.times[-1])
        t_target = t_last + horizon_sec
        X_target = np.array([[t_target - self._t_mean]])
        p = self.model.predict(X_target)[0]
        return {"pred": float(p), "rmse": float(self._rmse), "n": len(self.values)}

# --------------------
# Online predictor wrapper
# --------------------
@dataclass
class OnlinePredictor:
    sample_rate: float = 4.0
    short_window_sec: int = 300  # окно для краткосрочного предсказания (5 минут)
    model: Any = field(default=None, init=False)

    def __post_init__(self):
        # загружаем долгосрочную модель (если есть)
        try:
            self.model = load_risk_model()
        except Exception:
            self.model = None

    def predict_long(self, feature_vector: Dict[str, Any]) -> Dict[str, Any]:
        """
        Применить загруженную модель к вектору признаков.
        Возвращает словарь с probability / class (если доступно).
        """
        if self.model is None:
            return {"error": "no_model_loaded"}
        # Собираем числовой вектор — здесь нужно согласовать порядок признаков с тем, как обучалась модель.
        # Для примера: модель обучалась на ["decel_count","tachy_count","brady_count","stv_mean","age","Ph","Glu","LAC"]
        # Подстрой свой pipeline под реальную тренировку.
        feature_order = [
            "decel_count", "tachy_count", "brady_count", "stv_mean",
            "age", "gestation_weeks", "Ph", "Glu", "LAC", "BE"
        ]
        X = []
        for k in feature_order:
            v = feature_vector.get(k, None)
            try:
                X.append(float(v) if v is not None else 0.0)
            except Exception:
                X.append(0.0)
        try:
            proba = self.model.predict_proba([X])[0].tolist() if hasattr(self.model, "predict_proba") else None
            pred = int(self.model.predict([X])[0])
            return {"class": pred, "proba": proba}
        except Exception as e:
            return {"error": str(e)}

# --------------------
# Session-level state
# --------------------
@dataclass
class OnlineSessionState:
    session_id: str
    predictor: OnlinePredictor
    patient_info: Dict[str, Any] = field(default_factory=dict)

    # буферы (в секундах * sample_rate)
    bpm_forecaster: ShortTermForecaster = field(init=False)
    uter_forecaster: ShortTermForecaster = field(init=False)
    # последний вычисленный фичсет
    _last_features: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        sr = self.predictor.sample_rate
        self.bpm_forecaster = ShortTermForecaster(window_sec=self.predictor.short_window_sec, sample_rate=sr)
        self.uter_forecaster = ShortTermForecaster(window_sec=self.predictor.short_window_sec, sample_rate=sr)

        # ring buffer of raw values (for feature computation)
        self._time_buffer = deque(maxlen=int(self.predictor.short_window_sec * sr))
        self._bpm_buffer = deque(maxlen=int(self.predictor.short_window_sec * sr))
        self._uter_buffer = deque(maxlen=int(self.predictor.short_window_sec * sr))

    def update_patient_info(self, info: Dict[str, Any]):
        self.patient_info.update(info)

    def update_stream(self, t: float, bpm: Optional[float], uterus: Optional[float]):
        # add to raw buffer
        self._time_buffer.append(float(t))
        self._bpm_buffer.append(float(bpm) if bpm is not None else np.nan)
        self._uter_buffer.append(float(uterus) if uterus is not None else np.nan)
        # update forecasters (skip nan)
        if bpm is not None and not math.isnan(bpm):
            self.bpm_forecaster.update(t, bpm)
        if uterus is not None and not math.isnan(uterus):
            self.uter_forecaster.update(t, uterus)

        # recompute features
        self._last_features = compute_features_from_buffer(
            times=np.array(self._time_buffer, dtype=float),
            bpm=np.array(self._bpm_buffer, dtype=float),
            uterus=np.array(self._uter_buffer, dtype=float),
            patient_info=self.patient_info,
            sample_rate=self.predictor.sample_rate
        )

    def predict_short(self, horizons_sec: List[int] = [300, 600]) -> Dict[str, Any]:
        res = {}
        for h in horizons_sec:
            bpm_pred = self.bpm_forecaster.forecast(h)
            uter_pred = self.uter_forecaster.forecast(h)
            res[str(h)] = {"bpm": bpm_pred, "uterus": uter_pred}
        return res

    def predict_long(self) -> Dict[str, Any]:
        # использует predictor.model + self._last_features
        return self.predictor.predict_long(self._last_features)

    def current_features(self) -> Dict[str, Any]:
        return self._last_features
