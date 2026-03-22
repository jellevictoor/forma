"""Tests for schedule adjustment suggestions."""

from datetime import date, datetime, timedelta, timezone

from forma.domain.athlete import ScheduleTemplateSlot
from forma.domain.schedule_suggestions import suggest_schedule_changes
from forma.domain.workout import Workout, WorkoutType


def _slot(day: int, sport: str = "run") -> ScheduleTemplateSlot:
    return ScheduleTemplateSlot(workout_type=WorkoutType(sport), day_of_week=day)


def _workout_on(d: date) -> Workout:
    return Workout(
        id=f"w-{d.isoformat()}",
        athlete_id="a1",
        workout_type=WorkoutType.RUN,
        name="Run",
        start_time=datetime.combine(d, datetime.min.time()).replace(tzinfo=timezone.utc),
        duration_seconds=3600,
    )


def test_no_suggestions_when_no_schedule():
    result = suggest_schedule_changes([], [])

    assert result == []


def test_no_suggestion_when_all_days_hit():
    today = date.today()
    schedule = [_slot(today.weekday())]
    workouts = [_workout_on(today - timedelta(weeks=w)) for w in range(4)]

    result = suggest_schedule_changes(schedule, workouts)

    assert len(result) == 0


def test_suggestion_when_day_missed_repeatedly():
    today = date.today()
    # Schedule a day that has zero workouts
    empty_day = (today.weekday() + 3) % 7
    schedule = [_slot(empty_day)]

    result = suggest_schedule_changes(schedule, [], weeks=4)

    assert len(result) == 1
    assert result[0]["missed_count"] >= 2
