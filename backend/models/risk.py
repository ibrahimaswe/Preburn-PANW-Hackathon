import numpy as np

def risk_row(r: dict):
    """
    Compute burnout risk score, level, and top contributors
    from a single row of daily metrics (dict-like).
    """

    # Normalized terms
    sleep_term = np.clip(r.get("sleep_debt", 0) / 3.0, 0, 1)
    rhr_term   = np.clip((r.get("resting_hr_bpm", 58) - 58) / 15.0, 0, 1)
    hrv_term   = np.clip((60 - r.get("hrv_rmssd_ms", 60)) / 40.0, 0, 1)
    sent_term  = np.clip((0 - r.get("sentiment", 0)) / 1.2, 0, 1)
    work_term  = np.clip(r.get("workload_index", 0) / 10.0, 0, 1)

    score = float(
        np.clip(
            0.15
            + 0.28 * sleep_term
            + 0.20 * rhr_term
            + 0.22 * hrv_term
            + 0.15 * sent_term
            + 0.20 * work_term,
            0, 1
        )
    )

    # Risk level
    level = "Low" if score < 0.33 else ("Medium" if score < 0.66 else "High")

    # Top contributors
    contribs = sorted([
        ("Sleep debt", 0.28 * sleep_term),
        ("Resting HR", 0.20 * rhr_term),
        ("HRV low",    0.22 * hrv_term),
        ("Sentiment",  0.15 * sent_term),
        ("Workload",   0.20 * work_term),
    ], key=lambda x: x[1], reverse=True)[:3]

    return score, level, [{"name": c, "weight": round(w, 3)} for c, w in contribs]
