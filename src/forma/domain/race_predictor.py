"""Race time predictions using the Riegel formula.

T2 = T1 × (D2 / D1) ^ 1.06

Uses the athlete's best recent effort at a known distance to predict
times at standard race distances.
"""

RACE_DISTANCES = {
    "5 km": 5000,
    "10 km": 10000,
    "Half marathon": 21097,
    "Marathon": 42195,
}

RIEGEL_EXPONENT = 1.06


def predict_race_times(
    known_distance_m: float,
    known_time_seconds: int,
) -> list[dict]:
    """Predict times for standard race distances from a known effort.

    Returns a list of dicts: {distance_label, distance_m, predicted_seconds, predicted_pace}.
    Only predicts distances longer than the known distance (extrapolation).
    """
    if known_distance_m <= 0 or known_time_seconds <= 0:
        return []

    results = []
    for label, dist_m in RACE_DISTANCES.items():
        ratio = dist_m / known_distance_m
        predicted_s = int(known_time_seconds * (ratio ** RIEGEL_EXPONENT))
        pace_s_per_km = predicted_s / (dist_m / 1000)
        pace_min = int(pace_s_per_km // 60)
        pace_sec = int(pace_s_per_km % 60)

        hours = predicted_s // 3600
        mins = (predicted_s % 3600) // 60
        secs = predicted_s % 60
        if hours > 0:
            time_str = f"{hours}:{mins:02d}:{secs:02d}"
        else:
            time_str = f"{mins}:{secs:02d}"

        results.append({
            "distance_label": label,
            "distance_m": dist_m,
            "predicted_seconds": predicted_s,
            "predicted_time": time_str,
            "predicted_pace": f"{pace_min}:{pace_sec:02d}/km",
        })

    return results
