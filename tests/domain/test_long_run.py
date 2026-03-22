"""Tests for long run detection."""

from datetime import datetime, timezone

from forma.domain.long_run import is_long_run, long_run_summary
from forma.domain.workout import Workout, WorkoutType


def _run(duration_min: int = 30, distance_km: float = 5.0) -> Workout:
    return Workout(
        id="w1", athlete_id="a1", workout_type=WorkoutType.RUN,
        name="Run", start_time=datetime.now(tz=timezone.utc),
        duration_seconds=duration_min * 60,
        distance_meters=distance_km * 1000,
    )


def test_short_run_is_not_long():
    assert not is_long_run(_run(30, 5.0))


def test_60min_run_is_long():
    assert is_long_run(_run(60, 8.0))


def test_10km_run_is_long():
    assert is_long_run(_run(50, 10.0))


def test_strength_is_never_long():
    w = Workout(
        id="w1", athlete_id="a1", workout_type=WorkoutType.STRENGTH,
        name="Strength", start_time=datetime.now(tz=timezone.utc),
        duration_seconds=90 * 60,
    )
    assert not is_long_run(w)


def test_summary_empty():
    result = long_run_summary([])
    assert result["count"] == 0


def test_summary_with_long_runs():
    runs = [_run(70, 12.0), _run(65, 11.0), _run(30, 5.0)]
    result = long_run_summary(runs)
    assert result["count"] == 2
    assert result["longest_km"] == 12.0
