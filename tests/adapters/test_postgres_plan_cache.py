"""Integration tests for PostgresPlanCache."""

from datetime import date, datetime, timezone

import pytest

from forma.adapters.postgres_plan_cache import PostgresPlanCache
from forma.adapters.postgres_storage import PostgresStorage
from forma.domain.athlete import Athlete
from forma.ports.plan_cache_repository import PlannedDay, WeeklyPlan


@pytest.fixture
async def athlete_id(pool):
    storage = PostgresStorage(pool)
    await storage.save(Athlete(id="athlete-plan", name="Plan Runner"))
    return "athlete-plan"


@pytest.fixture
def cache(pool):
    return PostgresPlanCache(pool)


def _plan() -> WeeklyPlan:
    return WeeklyPlan(
        rationale="Focus on base building.",
        generated_at=datetime(2025, 1, 13, 9, 0, tzinfo=timezone.utc),
        days=[
            PlannedDay(
                day=date(2025, 1, 13),
                workout_type="run",
                intensity="easy",
                duration_minutes=45,
                description="Easy recovery run.",
                exercises={"warmup": ["Light jog"]},
            ),
            PlannedDay(
                day=date(2025, 1, 14),
                workout_type="strength",
                intensity="moderate",
                duration_minutes=60,
                description="Full body strength.",
                exercises={},
            ),
        ],
    )


async def test_get_returns_none_when_not_cached(cache):
    result = await cache.get("nonexistent")

    assert result is None


async def test_save_and_get_plan_rationale(cache, athlete_id):
    await cache.save(athlete_id, _plan(), latest_activity_at=None)

    result = await cache.get(athlete_id)

    assert result.rationale == "Focus on base building."


async def test_save_and_get_plan_day_count(cache, athlete_id):
    await cache.save(athlete_id, _plan(), latest_activity_at=None)

    result = await cache.get(athlete_id)

    assert len(result.days) == 2


async def test_save_and_get_plan_day_workout_type(cache, athlete_id):
    await cache.save(athlete_id, _plan(), latest_activity_at=None)

    result = await cache.get(athlete_id)

    assert result.days[0].workout_type == "run"


async def test_update_day_exercises(cache, athlete_id):
    await cache.save(athlete_id, _plan(), latest_activity_at=None)
    new_exercises = {"main": ["Squats 3x10", "Deadlift 3x5"]}
    await cache.update_day_exercises(athlete_id, date(2025, 1, 14), new_exercises)

    result = await cache.get(athlete_id)

    assert result.days[1].exercises == {"main": ["Squats 3x10", "Deadlift 3x5"]}


async def test_invalidate_removes_plan(cache, athlete_id):
    await cache.save(athlete_id, _plan(), latest_activity_at=None)
    await cache.invalidate(athlete_id)

    result = await cache.get(athlete_id)

    assert result is None


async def test_save_overwrites_existing_plan(cache, athlete_id):
    await cache.save(athlete_id, _plan(), latest_activity_at=None)
    new_plan = WeeklyPlan(
        rationale="New rationale.",
        generated_at=datetime(2025, 1, 20, 9, 0, tzinfo=timezone.utc),
        days=[],
    )
    await cache.save(athlete_id, new_plan, latest_activity_at=None)

    result = await cache.get(athlete_id)

    assert result.rationale == "New rationale."
