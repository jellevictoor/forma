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
