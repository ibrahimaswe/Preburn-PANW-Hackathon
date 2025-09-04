
from .risk import risk_row

def forecast(df, days: int = 3):
    """
    Forecast burnout risk for the next couple of days using
    simple exponential smoothing on the last 7 days of risk scores.
    """

    if df.empty:
        return []

    scores = []
    for _, r in df.tail(7).iterrows():
        s, _, _ = risk_row(r.to_dict())
        scores.append(s)

    if not scores:
        return []

    # Exponential smoothing
    alpha = 0.5
    s = scores[0]
    for x in scores[1:]:
        s = alpha * x + (1 - alpha) * s

    # Project next days with gradual decay
    return [
        round(float(s * 0.95), 3),
        round(float(s * 0.92), 3),
        round(float(s * 0.90), 3),
    ]
