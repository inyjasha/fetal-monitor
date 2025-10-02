# app/ml/dataset.py
"""
Сбор датасета из папки data/ + excel меток.
Возвращает DataFrame с числовыми фичами, готовыми для обучения.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List
from .predict import compute_features_from_buffer

DATA_ROOT = Path("data")
EXCEL_HYPOXIA = Path("hypoxia.xlsx")
EXCEL_REGULAR = Path("regular.xlsx")

def load_excel_labels():
    hyp = pd.read_excel(EXCEL_HYPOXIA)
    reg = pd.read_excel(EXCEL_REGULAR)
    hyp["group"] = "hypoxia"
    reg["group"] = "regular"
    df = pd.concat([hyp, reg], ignore_index=True, sort=False)
    # Приводим folder_id (иногда диапазон/строка)
    df["folder_id"] = df["folder_id"].astype(str).str.split(",").str[0].str.strip()
    # бинарная метка
    df["label"] = (df["group"] == "hypoxia").astype(int)
    return df

def load_session_features(folder_path: Path):
    # читаем все bpm и uterus csv и делаем merged (упрощённо — как раньше)
    bpm_files = sorted((folder_path / "bpm").glob("*.csv"))
    uter_files = sorted((folder_path / "uterus").glob("*.csv"))
    if not bpm_files or not uter_files:
        raise FileNotFoundError("missing bpm or uterus files")

    bpm_df = pd.concat([pd.read_csv(p) for p in bpm_files], ignore_index=True)
    uter_df = pd.concat([pd.read_csv(p) for p in uter_files], ignore_index=True)

    bpm_df = bpm_df.rename(columns={"time_sec": "time", "value": "bpm"})
    uter_df = uter_df.rename(columns={"time_sec": "time", "value": "uterus"})

    # Merge asof by time
    merged = pd.merge_asof(bpm_df.sort_values("time"), uter_df.sort_values("time"), on="time", direction="nearest")
    # compute features from the entire merged file
    feats = compute_features_from_buffer(merged["time"].to_numpy(), merged["bpm"].to_numpy(), merged["uterus"].to_numpy(), patient_info={})
    # flatten selected numeric features for training
    row = {
        "decel_count": feats.get("decel_count", 0),
        "tachy_count": feats.get("tachy_count", 0),
        "brady_count": feats.get("brady_count", 0),
        "stv_mean": feats.get("stv_mean"),
        "last_bpm": feats.get("last_bpm"),
        "last_uterus": feats.get("last_uterus")
    }
    return row

def build_dataset():
    df = load_excel_labels()
    rows = []
    for _, r in df.iterrows():
        folder_id = r["folder_id"]
        group = r["group"]
        folder_path = DATA_ROOT / group / str(folder_id)
        if not folder_path.exists():
            continue
        try:
            feats = load_session_features(folder_path)
            feats.update({
                "folder_id": folder_id,
                "group": group,
                "label": r["label"],
                "Ph": r.get("Ph"),
                "Glu": r.get("Glu"),
                "LAC": r.get("LAC"),
                "BE": r.get("BE"),
                "age": r.get("age") if "age" in r.index else None,
                "gestation_weeks": r.get("gestation_weeks") if "gestation_weeks" in r.index else None
            })
            rows.append(feats)
        except Exception as e:
            print("skip", folder_path, e)
    return pd.DataFrame(rows)
