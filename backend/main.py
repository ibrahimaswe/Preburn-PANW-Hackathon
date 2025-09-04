from fastapi import FastAPI, UploadFile, File  # pyright: ignore[reportMissingImports]
from typing import List, Dict
import os
import json
import pandas as pd
import numpy as np
from pathlib import Path
from models.features import compute_features
from models.risk import risk_row
from models.forecast import forecast
from models.ml import train_risk_model, predict_risk, risk_level, explain_row_with_shap, prophet_forecast_from_history

# openai is optional
try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

app = FastAPI(title="PreBurn API")

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "merged_burnout_schema_sample.csv"
df = pd.read_csv(DATA_PATH, parse_dates=["date"])

# Train lightweight model at startup 
ml_model, ml_features = train_risk_model(df)

@app.get("/risk")
def get_risk():
    dfd = compute_features(df)
    today_row = dfd.iloc[-1]
    # Prefer ML prediction if available
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
    
    global ml_model, ml_features
    ml_model, ml_features = train_risk_model(df)
    return {"rows": len(df), "ok": True}


def _summarize_contributors(contribs: List[Dict]) -> str:
    names = [c.get("name", "").lower() for c in contribs]
    return ", ".join(names)


def _fallback_actions(today: Dict, score: float, level: str, contribs: List[Dict]) -> List[Dict]:
    """Generate simple, reasoned actions without LLM, based on contributors."""
    actions: List[Dict] = []
    names = {c["name"].lower(): c["weight"] for c in contribs}

    sleep_debt = float(today.get("sleep_debt", 0) or 0)
    workload = float(today.get("workload_index", 0) or 0)
    rhr = float(today.get("resting_hr_bpm", 58) or 58)
    hrv = float(today.get("hrv_rmssd_ms", 60) or 60)
    sentiment = float(today.get("sentiment", 0) or 0)

    # 1) Regulate stress (HRV / RHR)
    if "hrv low" in names or rhr > 70:
        actions.append({
            "title": "3‑min paced breathing",
            "explanation": (
                "HRV appears suppressed and/or resting HR is elevated. Paced breathing can increase vagal tone "
                "and down‑shift sympathetic arousal, reducing near‑term burnout risk."
            )
        })

    # 2) Short walk break for mood and recovery
    if "sentiment" in names or sentiment < 0:
        actions.append({
            "title": "10‑min outdoor walk",
            "explanation": (
                "Mood and cognitive load signals suggest strain. A brief walk improves affect and restores attention, "
                "supporting recovery without impacting schedule."
            )
        })

    # 3) Workload management
    if "workload" in names or workload >= 6:
        actions.append({
            "title": "Block a 45‑min focus hour",
            "explanation": (
                "Workload is a leading contributor today. A protected focus block reduces context switches and lowers "
                "perceived load, which helps the risk drivers."
            )
        })

    # 4) Sleep debt remediation
    if "sleep debt" in names or sleep_debt >= 1.0:
        actions.append({
            "title": "Advance bedtime by 30 minutes",
            "explanation": (
                "Sleep debt is elevated. Banking 30 extra minutes tonight helps normalize autonomic balance and next‑day resilience."
            )
        })

    # Ensure at least three items (pad with sensible defaults if needed)
    defaults = [
        {"title": "3‑min paced breathing", "explanation": "Quick autonomic reset to reduce stress reactivity."},
        {"title": "10‑min outdoor walk", "explanation": "Light movement to lift mood and restore focus."},
        {"title": "Block a 45‑min focus hour", "explanation": "Lower workload by eliminating context switching."},
    ]
    if len(actions) < 3:
        have = {a["title"] for a in actions}
        for d in defaults:
            if d["title"] not in have:
                actions.append(d)
            if len(actions) >= 3:
                break
    return actions[:3]


def _day_specific_actions(day: int, today: Dict, target_score: float, contribs: List[Dict]) -> List[Dict]:
    """Return 1–2 day‑specific actions that differ across days.
    Uses simple category rotation to ensure variety.
    """
    # Action templates (kept concise and practical)
    catalog: Dict[str, Dict[str, str]] = {
        "breathing": {
            "title": "3‑min paced breathing",
            "explanation": "Reset autonomic balance to lower stress reactivity before the day."
        },
        "walk": {
            "title": "10‑min outdoor walk",
            "explanation": "Light movement to lift mood and restore focus between tasks."
        },
        "focus_block": {
            "title": "Block a 45‑min focus hour",
            "explanation": "Reduce context switches to lower mental load and perceived workload."
        },
        "bedtime": {
            "title": "Advance bedtime by 30 minutes",
            "explanation": "Bank extra sleep to improve recovery and next‑day resilience."
        },
        "caffeine_cutoff": {
            "title": "No caffeine after 2pm",
            "explanation": "Protect tonight’s sleep depth and HRV for better recovery."
        },
        "micro_recovery": {
            "title": "Schedule a 15‑min micro‑recovery",
            "explanation": "Short break (stretching or quiet time) to downshift arousal later today."
        },
    }

    # Map day → categories to ensure variety
    day_idx = max(1, min(3, int(day)))
    if day_idx == 1:
        order = ["breathing", "walk", "focus_block"]
    elif day_idx == 2:
        order = ["focus_block", "bedtime", "walk"]
    else:
        order = ["caffeine_cutoff", "micro_recovery", "breathing"]

    # Risk‑aware count: fewer if risk is low
    num = 1 if float(target_score) < 0.3 else 2
    picked: List[Dict] = []
    seen = set()
    for key in order:
        if key in seen:
            continue
        picked.append(catalog[key])
        seen.add(key)
        if len(picked) >= num:
            break
    return picked


@app.get("/actions")
def get_actions(source: str = "auto", diag: bool = False, day: int = 0):
    """
    Return recommended actions with explanations. Uses OpenAI.
    otherwise falls back to rule-based reasoning from model contributors.
    """
    dfd = compute_features(df)
    today_row = dfd.iloc[-1]

    # Derive score, level, and contributors similar to /risk (today context)
    ml_score = predict_risk(ml_model, ml_features, today_row)
    if ml_score is not None:
        score = float(np.clip(ml_score, 0, 1))
        level = risk_level(score)
        contribs = explain_row_with_shap(ml_model, ml_features, today_row)
    else:
        score, level, contribs = risk_row(today_row.to_dict())

    # If a future day is requested, use forecast to set target score/level
    target_score = score
    target_level = level
    if isinstance(day, int) and day > 0:
        # Build history and forecast next 3 days
        hist_scores: List[float] = []
        for _, r in dfd.iterrows():
            ml_s = predict_risk(ml_model, ml_features, r)
            if ml_s is None:
                s, _, _ = risk_row(r.to_dict())
                hist_scores.append(s)
            else:
                hist_scores.append(ml_s)
        history = pd.DataFrame({"date": dfd["date"], "risk_score": hist_scores})
        fc = prophet_forecast_from_history(history, days=3)
        if fc is None:
            fc = forecast(dfd)
        idx = max(1, min(3, int(day))) - 1
        if isinstance(fc, list) and len(fc) > idx:
            target_score = float(np.clip(fc[idx], 0, 1))
            target_level = risk_level(target_score)

    # Choose generation source: prefer LLM, then fallback to rules
    diagnostics: Dict = {
        "has_api_key": bool(os.environ.get("OPENAI_API_KEY")),
        "openai_imported": OpenAI is not None,
    }
    want_llm = source.lower() in ("auto", "llm") and not (isinstance(day, int) and day > 0)
    if want_llm:
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key and OpenAI is not None:
            try:
                client = OpenAI(api_key=api_key)
                for_day = f" for +{int(day)}d" if isinstance(day, int) and day > 0 else ""
                prompt = (
                    "Given today's context, propose concise, practical actions with a one‑sentence explanation each.\n"
                    f"Target{for_day} risk level: {target_level} (score {round(target_score,3)}). Today's top contributors: {_summarize_contributors(contribs)}.\n"
                    "For +Nd horizons, generate ONLY 1–2 actions and ensure they differ from other days' suggestions (no repeated titles).\n"
                    "Consider physiology (HRV, resting HR), workload, sleep debt, and mood.\n"
                    "Return strict JSON with key 'actions' as a list of {title, explanation}."
                )
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a health behavior coach. Be specific and concise."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.4,
                    max_tokens=300,
                    response_format={"type": "json_object"},
                )
                content = resp.choices[0].message.content or ""
                data = json.loads(content)
                actions = data.get("actions", [])
                if isinstance(actions, list) and actions:
                    return {"actions": actions, "source": "llm", **({"diagnostics": diagnostics} if diag else {})}
            except Exception as e:
                # Fall through to rules
                diagnostics["llm_error"] = str(e)[:200]
        else:
            diagnostics["llm_error"] = "missing_api_key_or_client"

    if source.lower() == "llm":
        # Explicit LLM requested but unavailable
        if isinstance(day, int) and day > 0:
            acts = _day_specific_actions(day, today_row.to_dict(), target_score, contribs)
        else:
            acts = _fallback_actions(today_row.to_dict(), score, level, contribs)
        return {"actions": acts, "source": "rules", **({"diagnostics": diagnostics} if diag else {})}

    if isinstance(day, int) and day > 0:
        actions = _day_specific_actions(day, today_row.to_dict(), target_score, contribs)
    else:
        actions = _fallback_actions(today_row.to_dict(), target_score, target_level, contribs)
    return {"actions": actions, "source": "rules", **({"diagnostics": diagnostics} if diag else {})}