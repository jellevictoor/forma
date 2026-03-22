"""Pure domain logic for swapping plan days."""

from datetime import date

from forma.domain.athlete import ScheduleTemplateSlot
from forma.ports.plan_cache_repository import PlannedDay

INTENSITY_WEIGHT = {
    "rest": 0,
    "recovery": 1,
    "easy": 2,
    "moderate": 3,
    "tempo": 4,
    "threshold": 5,
    "hard": 5,
}


def find_swap_target(
    days: list[PlannedDay],
    skip_date: date,
    constraints: list[ScheduleTemplateSlot],
) -> date | None:
    """Find the best day to swap with the skipped day.

    Priority: nearest rest day, then lightest intensity day.
    Respects schedule template constraints.
    """
    skipped = _find_day(days, skip_date)
    if not skipped:
        return None

    candidates = [d for d in days if d.day != skip_date]
    if not candidates:
        return None

    constraint_map = _build_constraint_map(constraints)

    valid = []
    for candidate in candidates:
        if not _swap_is_valid(skipped, candidate, constraint_map):
            continue
        valid.append(candidate)

    if not valid:
        return None

    # Prefer rest days first, then lowest intensity, then nearest
    def sort_key(d: PlannedDay) -> tuple:
        is_rest = d.workout_type == "rest"
        weight = INTENSITY_WEIGHT.get(d.intensity, 3)
        distance = abs((d.day - skip_date).days)
        return (not is_rest, weight, distance)

    valid.sort(key=sort_key)
    return valid[0].day


def swap_days(days: list[PlannedDay], date_a: date, date_b: date) -> list[PlannedDay]:
    """Swap the workout content of two days, preserving the dates."""
    result = []
    day_a = _find_day(days, date_a)
    day_b = _find_day(days, date_b)
    if not day_a or not day_b:
        return days

    for d in days:
        if d.day == date_a:
            result.append(PlannedDay(
                day=date_a,
                workout_type=day_b.workout_type,
                intensity=day_b.intensity,
                duration_minutes=day_b.duration_minutes,
                description=day_b.description,
                exercises=day_b.exercises,
            ))
        elif d.day == date_b:
            result.append(PlannedDay(
                day=date_b,
                workout_type=day_a.workout_type,
                intensity=day_a.intensity,
                duration_minutes=day_a.duration_minutes,
                description=day_a.description,
                exercises=day_a.exercises,
            ))
        else:
            result.append(d)
    return result


def _find_day(days: list[PlannedDay], target: date) -> PlannedDay | None:
    for d in days:
        if d.day == target:
            return d
    return None


def _build_constraint_map(constraints: list[ScheduleTemplateSlot]) -> dict[int, str]:
    """Map day_of_week -> required workout_type."""
    return {c.day_of_week: c.workout_type.value for c in constraints}


def _swap_is_valid(
    skipped: PlannedDay,
    candidate: PlannedDay,
    constraint_map: dict[int, str],
) -> bool:
    """Check if swapping these two days would violate constraints."""
    skip_dow = skipped.day.weekday()
    cand_dow = candidate.day.weekday()

    # Would putting the skipped workout on the candidate's day violate a constraint?
    if cand_dow in constraint_map and constraint_map[cand_dow] != skipped.workout_type:
        return False

    # Would putting the candidate's workout on the skipped day violate a constraint?
    if skip_dow in constraint_map and constraint_map[skip_dow] != candidate.workout_type:
        return False

    return True
