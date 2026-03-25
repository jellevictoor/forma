"""Tests for plan matching."""

from datetime import date, datetime, timedelta, timezone

from forma.domain.plan_match import match_workout_to_plan, types_compatible
from forma.domain.workout import Workout, WorkoutType
from forma.ports.plan_cache_repository import PlannedDay


def _workout(sport: str = "run") -> Workout:
    d = date.today()
    return Workout(
        id="w1", athlete_id="a1", workout_type=WorkoutType(sport),
        name="Test", start_time=datetime.combine(d, datetime.min.time()).replace(tzinfo=timezone.utc),
        duration_seconds=3600,
    )


def _plan_day(sport: str = "run", desc: str = "Easy run", exercises=None) -> PlannedDay:
    return PlannedDay(
        day=date.today(), workout_type=sport, intensity="easy",
        duration_minutes=45, description=desc,
        exercises=exercises or {},
    )


def test_exact_type_match():
    result = match_workout_to_plan(_workout("run"), [_plan_day("run", desc="Easy 40min run")])

    assert result.description == "Easy 40min run"


def test_match_includes_exercises():
    exercises = {"warmup": ["5 min jog"], "main": ["3x10 Deadlift"]}
    result = match_workout_to_plan(_workout("run"), [_plan_day("run", exercises=exercises)])

    assert result.exercises == exercises


def test_match_without_exercises():
    result = match_workout_to_plan(_workout("run"), [_plan_day("run")])

    assert result.exercises is None


def test_compatible_type_match():
    assert types_compatible("strength", "cross_training")
    assert types_compatible("run", "trail_run")
    assert types_compatible("climbing", "rock_climbing")


def test_incompatible_type_no_match():
    result = match_workout_to_plan(_workout("strength"), [_plan_day("run")])

    assert result is None


def test_different_date_no_match():
    plan = PlannedDay(
        day=date.today() + timedelta(days=1), workout_type="run",
        intensity="easy", duration_minutes=45, description="Tomorrow",
    )
    result = match_workout_to_plan(_workout("run"), [plan])

    assert result is None


def test_rest_day_not_matched():
    result = match_workout_to_plan(_workout("run"), [_plan_day("rest")])

    assert result is None


def test_no_plan_days():
    result = match_workout_to_plan(_workout("run"), [])

    assert result is None
