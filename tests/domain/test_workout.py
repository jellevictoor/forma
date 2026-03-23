"""Tests for Workout domain model."""

from datetime import datetime

import pytest

from forma.domain.workout import Workout, WorkoutType


def _make_workout(**kwargs) -> Workout:
    defaults = {
        "id": "w1",
        "athlete_id": "a1",
        "workout_type": WorkoutType.RUN,
        "name": "Test",
        "start_time": datetime(2026, 3, 23, 8, 0),
        "duration_seconds": 3600,
    }
    defaults.update(kwargs)
    return Workout(**defaults)


def test_ebike_is_valid_workout_type():
    w = _make_workout(workout_type=WorkoutType.EBIKE)

    assert w.workout_type == WorkoutType.EBIKE


def test_ebike_value_is_ebike():
    assert WorkoutType.EBIKE.value == "ebike"


def test_speed_kmh_from_average_speed():
    w = _make_workout(average_speed_mps=5.0)

    assert w.speed_kmh == pytest.approx(18.0)


def test_speed_kmh_returns_none_without_speed():
    w = _make_workout()

    assert w.speed_kmh is None


def test_speed_formatted_returns_string():
    w = _make_workout(average_speed_mps=6.944)

    assert w.speed_formatted() == "25.0 km/h"


def test_speed_formatted_returns_none_without_speed():
    w = _make_workout()

    assert w.speed_formatted() is None


def test_average_watts_stored():
    w = _make_workout(average_watts=150.0)

    assert w.average_watts == 150.0


def test_average_watts_defaults_to_none():
    w = _make_workout()

    assert w.average_watts is None
