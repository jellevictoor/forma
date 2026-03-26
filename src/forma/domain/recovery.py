"""Recovery time estimation based on workout effort and current form."""


def estimate_recovery_hours(
    duration_minutes: float,
    average_heartrate: float | None,
    max_heartrate: float | None,
    form: float,
) -> int:
    """Estimate hours until ready for next hard session.

    Factors:
    - Workout intensity (HR as % of max, or duration if no HR)
    - Workout duration
    - Current form (negative = already fatigued, needs more recovery)
    """
    # Base recovery from duration
    if duration_minutes < 30:
        base_hours = 12
    elif duration_minutes < 60:
        base_hours = 24
    elif duration_minutes < 90:
        base_hours = 36
    else:
        base_hours = 48

    # Intensity multiplier from HR
    if average_heartrate and max_heartrate and max_heartrate > 0:
        hr_pct = average_heartrate / max_heartrate
        if hr_pct > 0.85:
            base_hours = int(base_hours * 1.5)
        elif hr_pct < 0.65:
            base_hours = int(base_hours * 0.7)

    # Form adjustment — fatigued athletes need more recovery (Banister thresholds)
    if form < -30:
        base_hours = int(base_hours * 1.5)
    elif form < -10:
        base_hours = int(base_hours * 1.3)
    elif form < 0:
        base_hours = int(base_hours * 1.1)
    elif form > 10:
        base_hours = int(base_hours * 0.8)

    return max(6, min(72, base_hours))


def recovery_label(hours: int) -> str:
    """Human-readable recovery suggestion."""
    if hours <= 12:
        return "Ready for another session"
    if hours <= 24:
        return "Light activity tomorrow, hard session in 2 days"
    if hours <= 36:
        return "Easy day tomorrow recommended"
    if hours <= 48:
        return "Take a rest day before your next hard session"
    return "Extended recovery needed — prioritise sleep and nutrition"
