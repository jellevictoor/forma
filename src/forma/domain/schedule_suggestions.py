"""Schedule adjustment suggestions based on missed day patterns."""

from datetime import date, timedelta

from forma.domain.athlete import ScheduleTemplateSlot
from forma.domain.workout import Workout

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MISS_THRESHOLD = 2  # missed 2+ times in 4 weeks → suggest change


def suggest_schedule_changes(
    schedule: list[ScheduleTemplateSlot],
    workouts: list[Workout],
    weeks: int = 4,
) -> list[dict]:
    """Check if scheduled days are consistently missed and suggest changes.

    Returns list of suggestions: {day_name, sport, missed_count, total_weeks, suggestion}.
    """
    if not schedule:
        return []

    today = date.today()
    since = today - timedelta(weeks=weeks)
    workout_dates = {w.start_time.date() for w in workouts if w.start_time.date() >= since}

    suggestions = []
    for slot in schedule:
        missed = 0
        for w in range(weeks):
            week_start = since + timedelta(weeks=w)
            target_day = week_start + timedelta(days=(slot.day_of_week - week_start.weekday()) % 7)
            if target_day > today:
                continue
            if target_day not in workout_dates:
                missed += 1

        if missed >= MISS_THRESHOLD:
            day_name = DAY_NAMES[slot.day_of_week]
            sport = slot.workout_type.value.replace("_", " ").title()
            suggestions.append({
                "day_name": day_name,
                "sport": sport,
                "missed_count": missed,
                "total_weeks": weeks,
                "suggestion": f"You've missed {day_name} {sport.lower()} {missed} of the last {weeks} weeks. Consider moving it to a different day.",
            })

    return suggestions
