import pandas as pd
import numpy as np

def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Given a daily-metrics DataFrame (with at least `date`),
    compute rolling baselines, z-scores, and derived features.
    Returns a new DataFrame with added columns.
    """

    if df.empty:
        return df

    # Ensure date is sorted
    df = df.sort_values("date").copy()

    # Rolling baselines for core signals
    for col in ["sleep_hours", "resting_hr_bpm", "hrv_rmssd_ms", "steps", "sentiment", "meeting_minutes"]:
        if col in df:
            df[f"{col}_mean7"] = df[col].rolling(7, min_periods=3).mean()
            df[f"{col}_std7"] = df[col].rolling(7, min_periods=3).std()
            df[f"{col}_z"] = (df[col] - df[f"{col}_mean7"]) / (df[f"{col}_std7"] + 1e-6)

    # Derived features
    df["sleep_debt"] = (7.5 - df.get("sleep_hours", 7.5)).clip(lower=0)

    if "workload_index" not in df:
        df["workload_index"] = (
            df.get("meeting_minutes", 0) / 60.0
            + 0.5 * df.get("after_hours_meetings", 0).fillna(0)
        )

    return df
