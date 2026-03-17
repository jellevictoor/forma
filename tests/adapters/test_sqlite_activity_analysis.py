"""Tests for SQLiteActivityAnalysis adapter."""

import pytest

from forma.adapters.sqlite_activity_analysis import SQLiteActivityAnalysis
from forma.ports.activity_analysis_repository import ActivityAnalysis


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def cache(db_path):
    return SQLiteActivityAnalysis(db_path)


def _sample_analysis(**overrides):
    defaults = dict(
        performance_assessment="Solid tempo run.",
        training_load_context="You were fresh going in.",
        goal_relevance="Directly supports your 10k goal.",
        comparison_to_recent="Faster than your last 3 runs.",
        takeaway="Keep this intensity for mid-week sessions.",
    )
    defaults.update(overrides)
    return ActivityAnalysis(**defaults)


async def test_get_returns_none_when_not_cached(cache):
    result = await cache.get("workout-1")

    assert result is None


async def test_get_returns_analysis_after_save(cache):
    await cache.save("workout-1", _sample_analysis())

    result = await cache.get("workout-1")

    assert result is not None


async def test_cached_analysis_has_correct_workout_id(cache):
    await cache.save("workout-1", _sample_analysis())

    result = await cache.get("workout-1")

    assert result.workout_id == "workout-1"


async def test_cached_analysis_has_correct_performance_assessment(cache):
    await cache.save("workout-1", _sample_analysis(performance_assessment="Great run."))

    result = await cache.get("workout-1")

    assert result.analysis.performance_assessment == "Great run."


async def test_cached_analysis_has_correct_takeaway(cache):
    await cache.save("workout-1", _sample_analysis(takeaway="Rest tomorrow."))

    result = await cache.get("workout-1")

    assert result.analysis.takeaway == "Rest tomorrow."


async def test_save_overwrites_existing(cache):
    await cache.save("workout-1", _sample_analysis(takeaway="First."))
    await cache.save("workout-1", _sample_analysis(takeaway="Second."))

    result = await cache.get("workout-1")

    assert result.analysis.takeaway == "Second."


async def test_invalidate_removes_cached_analysis(cache):
    await cache.save("workout-1", _sample_analysis())
    await cache.invalidate("workout-1")

    result = await cache.get("workout-1")

    assert result is None


async def test_invalidate_nonexistent_does_not_raise(cache):
    await cache.invalidate("nonexistent")


async def test_different_workouts_have_separate_caches(cache):
    await cache.save("workout-1", _sample_analysis(takeaway="First workout."))
    await cache.save("workout-2", _sample_analysis(takeaway="Second workout."))

    result_1 = await cache.get("workout-1")
    await cache.get("workout-2")

    assert result_1.analysis.takeaway == "First workout."


async def test_different_workouts_are_independent(cache):
    await cache.save("workout-1", _sample_analysis(takeaway="First workout."))
    await cache.save("workout-2", _sample_analysis(takeaway="Second workout."))

    result_2 = await cache.get("workout-2")

    assert result_2.analysis.takeaway == "Second workout."
