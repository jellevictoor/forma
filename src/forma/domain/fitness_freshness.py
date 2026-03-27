"""Fitness/Fatigue/Form (CTL/ATL) model — pure fitness science domain logic."""

import math
from datetime import date, timedelta

_CTL_K = 42  # chronic training load time constant (days)
_ATL_K = 7   # acute training load time constant (days)
_CTL_DECAY = math.exp(-1 / _CTL_K)
_ATL_DECAY = math.exp(-1 / _ATL_K)
CTL_SEED_DAYS = _CTL_K * 2  # days before display window to seed CTL properly


def compute_fitness_freshness(daily_efforts: list[dict], display_days: int) -> list[dict]:
    today = date.today()
    display_start = today - timedelta(days=display_days - 1)
    seed_start = display_start - timedelta(days=CTL_SEED_DAYS)

    effort_by_date: dict[date, float] = {
        date.fromisoformat(d["date"]): d["effort"] for d in daily_efforts
    }

    ctl = 0.0
    atl = 0.0
    result = []
    current = seed_start

    while current <= today:
        effort = effort_by_date.get(current, 0.0)
        ctl = ctl * _CTL_DECAY + effort * (1 - _CTL_DECAY)
        atl = atl * _ATL_DECAY + effort * (1 - _ATL_DECAY)

        if current >= display_start:
            result.append({
                "date": current.isoformat(),
                "fitness": round(ctl, 1),
                "fatigue": round(atl, 1),
                "form": round(ctl - atl, 1),
                "effort": round(effort, 1),
            })

        current += timedelta(days=1)

    return result


def classify_form(form: float, ctl: float, atl: float) -> str:
    """Classify form/fatigue state using Banister model thresholds.

    Returns a human-readable context string for use in LLM prompts and UI.
    """
    overload_ratio = atl / ctl if ctl > 5 else 2.0
    if form > 10:
        return "fresh — ready for a quality session or goal event"
    if form > 0:
        return "good form — normal training, can include moderate intensity"
    if form > -10 and overload_ratio < 1.5:
        return "normal training fatigue — productive loading zone, easy/moderate mix"
    if form > -10:
        return "moderate fatigue with high relative load (ATL/CTL ratio high) — favour easy sessions, avoid intensity"
    if form > -30:
        return "fatigued — reduce intensity to easy/recovery, add an extra rest day"
    return "exhausted — recovery week, mostly rest with 1-2 light sessions max"


def compute_overload_ratio(ctl: float, atl: float) -> float:
    """ATL/CTL ratio — captures relative overload better than absolute TSB."""
    return atl / ctl if ctl > 5 else 2.0
