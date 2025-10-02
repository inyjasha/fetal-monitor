# app/ml/models.py
"""
Интерфейс модели долгосрочного риска.
Здесь:
 - load_risk_model() -> загружает joblib pipeline (scaler + model)
 - train_and_save_model(X, y, feature_names, out_path) -> обучает и сохраняет pipeline
"""

import os
from typing import List
import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODEL_DIR, exist_ok=True)
MODEL_PATH = os.path.join(MODEL_DIR, "risk_pipeline.pkl")

def load_risk_model():
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found at {MODEL_PATH}")
    return joblib.load(MODEL_PATH)

def train_and_save_model(X: pd.DataFrame, y: pd.Series, feature_names: List[str] = None, save_path: str = MODEL_PATH):
    """
    Обучаем pipeline (Scaler + RandomForest). X — DataFrame, y — Series.
    Сохраняем pipeline в save_path.
    """
    clf = RandomForestClassifier(n_estimators=200, random_state=42, class_weight="balanced")
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", clf)
    ])
    pipeline.fit(X, y)
    joblib.dump(pipeline, save_path)
    return pipeline
