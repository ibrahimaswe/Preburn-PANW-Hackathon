from fastapi import FastAPI, UploadFile, File
from typing import List, Dict
import pandas as pd
import numpy as np
from pathlib import Path
from models.features import compute_features
from models.risk import risk_row
from models.forecast import forecast
from models.ml import train_risk_model, predict_risk, risk_level, explain_row_with_shap, prophet_forecast_from_history

app = FastAPI(title="PreBurn API")

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "merged_burnout_schema_sample.csv"
df = pd.read_csv(DATA_PATH, parse_dates=["date"])

# Train a lightweight model at startup (best-effort)
ml_model, ml_features = train_risk_model(df)

@app.get("/risk")
def get_risk():
    dfd = compute_features(df)
    today_row = dfd.iloc[-1]
    # Prefer ML prediction if available, else heuristic
    ml_score = predict_risk(ml_model, ml_features, today_row)
    if ml_score is not None:
        score = float(np.clip(ml_score, 0, 1))
        level = risk_level(score)
        contribs = explain_row_with_shap(ml_model, ml_features, today_row)
    else:
        score, level, contribs = risk_row(today_row.to_dict())
    return {
        "date": str(today_row["date"].date()),
        "risk_score": round(float(score), 3),
        "risk_level": level,
        "top_contributors": contribs,
    }

@app.get("/forecast")
def get_forecast():
    dfd = compute_features(df)
    # Build history of risk (from ML if available)
    hist_scores: List[float] = []
    for _, r in dfd.iterrows():
        ml_score = predict_risk(ml_model, ml_features, r)
        if ml_score is None:
            s, _, _ = risk_row(r.to_dict())
            hist_scores.append(s)
        else:
            hist_scores.append(ml_score)
    history = pd.DataFrame({"date": dfd["date"], "risk_score": hist_scores})
    fc = prophet_forecast_from_history(history, days=3)
    if fc is None:
        # Fallback to simple smoothing
        forecasted = forecast(dfd)
        return {"forecast": forecasted}
    return {"forecast": fc}

@app.get("/history")
def get_history():
    """Return daily history with risk score and key metrics."""
    dfd = compute_features(df)
    out: List[Dict] = []
    for _, r in dfd.iterrows():
        ml_score = predict_risk(ml_model, ml_features, r)
        if ml_score is None:
            s, lvl, _ = risk_row(r.to_dict())
        else:
            s = float(np.clip(ml_score, 0, 1))
            lvl = risk_level(s)
        out.append({
            "date": str(pd.to_datetime(r["date"]).date()),
            "risk_score": round(float(s), 3),
            "risk_level": lvl,
            "sleep_hours": float(r.get("sleep_hours", np.nan)) if "sleep_hours" in r else None,
            "steps": float(r.get("steps", np.nan)) if "steps" in r else None,
            "resting_hr_bpm": float(r.get("resting_hr_bpm", np.nan)) if "resting_hr_bpm" in r else None,
            "hrv_rmssd_ms": float(r.get("hrv_rmssd_ms", np.nan)) if "hrv_rmssd_ms" in r else None,
            "sentiment": float(r.get("sentiment", np.nan)) if "sentiment" in r else None,
            "meeting_minutes": float(r.get("meeting_minutes", np.nan)) if "meeting_minutes" in r else None,
        })
    return {"history": out}

@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    global df
    newdf = pd.read_csv(file.file, parse_dates=["date"])
    df = newdf
    # retrain on ingestion
    global ml_model, ml_features
    ml_model, ml_features = train_risk_model(df)
    return {"rows": len(df), "ok": True}