# app/ml/train_model.py
import pandas as pd
from .dataset import build_dataset
from .models import train_and_save_model
import numpy as np

def prepare_training_df():
    df = build_dataset()
    # убираем строки с критическими NaN
    df = df.dropna(subset=["decel_count", "tachy_count", "brady_count", "stv_mean"])
    # выбираем колонки для обучения — синхронизируйте со models.predict_long feature_order
    X = df[["decel_count","tachy_count","brady_count","stv_mean","age","gestation_weeks","Ph","Glu","LAC","BE"]].fillna(0)
    y = df["label"]
    return X, y

if __name__ == "__main__":
    X, y = prepare_training_df()
    print("Train size:", len(X))
    model = train_and_save_model(X, y)
    print("Model saved.")
