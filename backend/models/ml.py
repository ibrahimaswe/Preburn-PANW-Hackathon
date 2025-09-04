import math
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

from .features import compute_features

try:
    from sklearn.ensemble import GradientBoostingRegressor
except Exception:  # pragma: no cover - optional dependency during hackathon
    GradientBoostingRegressor = None  # type: ignore

try:
    import shap  # type: ignore
except Exception:  # pragma: no cover
    shap = None  # type: ignore

try:
    from prophet import Prophet  # type: ignore
except Exception:  # pragma: no cover
    Prophet = None  # type: ignore


FeatureList = List[str]


def _select_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, FeatureList]:
    """
    Select a compact set of features for the ML model.
    Assumes `compute_features` has already been applied.
    """
    candidate_cols: FeatureList = [
        "sleep_debt",
        "resting_hr_bpm",
        "hrv_rmssd_ms",
        "sentiment",
        "workload_index",
        # z-scores (if present)
        "sleep_hours_z",
        "resting_hr_bpm_z",
        "hrv_rmssd_ms_z",
        "steps_z",
        "sentiment_z",
    ]
    cols = [c for c in candidate_cols if c in df.columns]
    X = df[cols].fillna(method="ffill").fillna(0.0)
    return X, cols


def train_risk_model(df_raw: pd.DataFrame):
    """
    Train a lightweight regressor to predict `risk_score` from engineered features.
    Returns (model, feature_names). If sklearn isn't available or target not present,
    returns (None, []).
    """
    if GradientBoostingRegressor is None:
        return None, []

    df = compute_features(df_raw)
    if "risk_score" not in df.columns:
        return None, []

    X, features = _select_features(df)
    y = df["risk_score"].astype(float)
    if len(X) < 5:
        return None, []

    model = GradientBoostingRegressor(random_state=42)
    model.fit(X, y)
    return model, features


def predict_risk(model, features: FeatureList, row: pd.Series) -> Optional[float]:
    if model is None or not features:
        return None
    x = row.reindex(features).fillna(method="ffill").fillna(0.0).to_frame().T
    pred = float(model.predict(x)[0])
    return float(np.clip(pred, 0.0, 1.0))


def risk_level(score: float) -> str:
    return "Low" if score < 0.33 else ("Medium" if score < 0.66 else "High")


def explain_row_with_shap(model, features: FeatureList, row: pd.Series):
    """
    Return top contributors using SHAP if available, else fall back to model feature importances
    (or a simple heuristic if not present).
    Output: List[{name, weight}]
    """
    # Fallback: use feature importances (tree-based models) if SHAP unavailable
    if model is None or not features:
        return []

    try:
        if shap is not None:
            x = row.reindex(features).fillna(method="ffill").fillna(0.0).to_frame().T
            explainer = shap.Explainer(model)
            values = explainer(x).values[0]
            contribs = list(zip(features, np.abs(values)))
        elif hasattr(model, "feature_importances_"):
            contribs = list(zip(features, np.abs(model.feature_importances_)))
        else:
            return []
        contribs = sorted(contribs, key=lambda t: t[1], reverse=True)[:3]
        # Normalize to comparable weights 0..1
        total = sum(w for _, w in contribs) or 1.0
        return [{"name": n.replace("_", " ").title(), "weight": round(float(w/total), 3)} for n, w in contribs]
    except Exception:
        return []


def prophet_forecast_from_history(history: pd.DataFrame, days: int = 3) -> Optional[List[float]]:
    """
    Use Prophet to forecast risk for the next N days given a dataset with
    columns [date, risk_score]. Returns a list of floats in [0,1]. If Prophet
    isn't available or training fails, returns None below
    """
    if Prophet is None:
        return None
    try:
        dfp = pd.DataFrame({"ds": pd.to_datetime(history["date"]), "y": history["risk_score"].astype(float)})
        m = Prophet(seasonality_mode="additive")
        m.fit(dfp)
        future = m.make_future_dataframe(periods=days)
        fcst = m.predict(future).tail(days)["yhat"].clip(lower=0.0, upper=1.0).tolist()
        return [round(float(x), 3) for x in fcst]
    except Exception:
        return None


