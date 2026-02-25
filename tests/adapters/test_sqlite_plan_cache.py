"""Tests for SQLitePlanCache adapter."""

from datetime import date, datetime, timezone

import pytest

from fitness_coach.adapters.sqlite_plan_cache import SQLitePlanCache
from fitness_coach.ports.plan_cache_repository import PlannedDay, WeeklyPlan


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def cache(db_path):
    return SQLitePlanCache(db_path)


def make_plan() -> WeeklyPlan:
    days = [
        PlannedDay(
            day=date(2026, 2, 25),
            workout_type="run",
            intensity="easy",
            duration_minutes=45,
            description="Easy recovery run.",
        )
    ]
    return WeeklyPlan(
        days=days,
        rationale="Focus on recovery after a hard week.",
        generated_at=datetime(2026, 2, 25, 8, 0, tzinfo=timezone.utc),
    )


async def test_get_returns_none_when_no_cache(cache):
    result = await cache.get("athlete1")

    assert result is None


async def test_get_returns_plan_after_save(cache):
    plan = make_plan()
    await cache.save("athlete1", plan, latest_activity_at=None)

    result = await cache.get("athlete1")

    assert result is not None


async def test_cached_plan_has_correct_rationale(cache):
    plan = make_plan()
    await cache.save("athlete1", plan, latest_activity_at=None)

    result = await cache.get("athlete1")

    assert result.rationale == "Focus on recovery after a hard week."


async def test_cached_plan_has_correct_number_of_days(cache):
    plan = make_plan()
    await cache.save("athlete1", plan, latest_activity_at=None)

    result = await cache.get("athlete1")

    assert len(result.days) == 1


async def test_cached_plan_day_has_correct_workout_type(cache):
    plan = make_plan()
    await cache.save("athlete1", plan, latest_activity_at=None)

    result = await cache.get("athlete1")

    assert result.days[0].workout_type == "run"


async def test_cached_plan_day_has_correct_intensity(cache):
    plan = make_plan()
    await cache.save("athlete1", plan, latest_activity_at=None)

    result = await cache.get("athlete1")

    assert result.days[0].intensity == "easy"


async def test_cached_plan_day_has_correct_date(cache):
    plan = make_plan()
    await cache.save("athlete1", plan, latest_activity_at=None)

    result = await cache.get("athlete1")

    assert result.days[0].day == date(2026, 2, 25)


async def test_save_overwrites_existing_plan(cache):
    first = make_plan()
    second = WeeklyPlan(
        days=[PlannedDay(day=date(2026, 2, 25), workout_type="strength", intensity="moderate", duration_minutes=60, description="Strength session.")],
        rationale="Build strength this week.",
        generated_at=datetime(2026, 2, 25, 9, 0, tzinfo=timezone.utc),
    )
    await cache.save("athlete1", first, latest_activity_at=None)
    await cache.save("athlete1", second, latest_activity_at=None)

    result = await cache.get("athlete1")

    assert result.rationale == "Build strength this week."


async def test_cached_plan_stores_latest_activity_at(cache):
    activity_time = datetime(2026, 2, 24, 10, 0, tzinfo=timezone.utc)
    plan = make_plan()
    await cache.save("athlete1", plan, latest_activity_at=activity_time)

    result = await cache.get("athlete1")

    assert result.latest_activity_at == activity_time


async def test_cached_plan_latest_activity_at_is_none_when_not_provided(cache):
    plan = make_plan()
    await cache.save("athlete1", plan, latest_activity_at=None)

    result = await cache.get("athlete1")

    assert result.latest_activity_at is None


async def test_invalidate_removes_cached_plan(cache):
    plan = make_plan()
    await cache.save("athlete1", plan, latest_activity_at=None)
    await cache.invalidate("athlete1")

    result = await cache.get("athlete1")

    assert result is None


async def test_update_day_exercises_stores_exercises(cache):
    plan = make_plan()
    await cache.save("athlete1", plan, latest_activity_at=None)
    exercises = {"warmup": ["5 min jog"], "main": ["3x10 squats"], "cooldown": ["stretch"]}
    await cache.update_day_exercises("athlete1", date(2026, 2, 25), exercises)

    result = await cache.get("athlete1")

    assert result.days[0].exercises == exercises


async def test_update_day_exercises_does_nothing_when_no_plan(cache):
    await cache.update_day_exercises("athlete1", date(2026, 2, 25), ["Warm-up: 5 min"])

    result = await cache.get("athlete1")

    assert result is None


async def test_cached_plan_day_exercises_default_to_empty_dict(cache):
    plan = make_plan()
    await cache.save("athlete1", plan, latest_activity_at=None)

    result = await cache.get("athlete1")

    assert result.days[0].exercises == {}


async def test_different_athletes_have_separate_caches(cache):
    plan_a = make_plan()
    plan_b = WeeklyPlan(
        days=[PlannedDay(day=date(2026, 2, 25), workout_type="climbing", intensity="moderate", duration_minutes=90, description="Climbing session.")],
        rationale="Climbing focus this week.",
        generated_at=datetime(2026, 2, 25, 8, 0, tzinfo=timezone.utc),
    )
    await cache.save("athlete_a", plan_a, latest_activity_at=None)
    await cache.save("athlete_b", plan_b, latest_activity_at=None)

    result_a = await cache.get("athlete_a")
    result_b = await cache.get("athlete_b")

    assert result_a.rationale == "Focus on recovery after a hard week."
    assert result_b.rationale == "Climbing focus this week."
