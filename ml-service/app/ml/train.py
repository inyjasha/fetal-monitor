# train.py
from ml.dataset import build_dataset
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib

df = build_dataset()
df = df.dropna()

X = df[["Ph","CO2","Glu","LAC","BE",
        "decelerations_count","tachy_count","brady_count","stv_mean"]]
y = df["label"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestClassifier(n_estimators=200, random_state=42)
model.fit(X_train, y_train)

print(classification_report(y_test, model.predict(X_test)))

joblib.dump(model, "ml/models/risk_model.pkl")
