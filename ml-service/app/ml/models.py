# ml/models.py
from sklearn.ensemble import RandomForestClassifier
import joblib
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models")

def load_risk_model():
    path = os.path.join(MODEL_PATH, "risk_model.pkl")
    return joblib.load(path)

def train_risk_model(X_train, y_train):
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    joblib.dump(model, os.path.join(MODEL_PATH, "risk_model.pkl"))
    return model
