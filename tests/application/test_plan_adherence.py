"""Tests for plan adherence computation."""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from forma.application.plan_adherence import PlanAdherenceService
from forma.domain.workout import Workout, WorkoutType
from forma.ports.plan_cache_repository import CachedWeeklyPlan, PlannedDay


def _planned_day(days_offset: int, sport: str = "run") -> PlannedDay:
    return PlannedDay(
        day=date.today() + timedelta(days=days_offset),
        workout_type=sport,
        intensity="easy",
        duration_minutes=45,
        description="Easy session",
    )


def _workout(days_offset: int, sport: str = "run", duration_min: int = 45) -> Workout:
    return Workout(
        id=f"w-{days_offset}",
        athlete_id="a1",
        workout_type=WorkoutType(sport),
        name="Session",
        start_time=datetime.now(tz=timezone.utc) + timedelta(days=days_offset),
        duration_seconds=duration_min * 60,
    )


def _make_service(plan_days, workouts) -> PlanAdherenceService:
    plan_cache = AsyncMock()
    plan_cache.get = AsyncMock(return_value=CachedWeeklyPlan(
        days=plan_days,
        rationale="Test",
        generated_at=datetime.now(tz=timezone.utc),
    ))
    workout_repo = AsyncMock()
    workout_repo.list_workouts_for_athlete = AsyncMock(return_value=workouts)
    return PlanAdherenceService(plan_cache, workout_repo)


@pytest.mark.asyncio
async def test_completed_day():
    service = _make_service(
        plan_days=[_planned_day(-1, "run")],
        workouts=[_workout(-1, "run")],
    )

    result = await service.get_adherence("a1")

    assert result[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_missed_day():
    service = _make_service(
        plan_days=[_planned_day(-1, "run")],
        workouts=[],
    )

    result = await service.get_adherence("a1")

    assert result[0]["status"] == "missed"


@pytest.mark.asyncio
async def test_upcoming_day():
    service = _make_service(
        plan_days=[_planned_day(1, "run")],
        workouts=[],
    )

    result = await service.get_adherence("a1")

    assert result[0]["status"] == "upcoming"


@pytest.mark.asyncio
async def test_completed_different_sport():
    service = _make_service(
        plan_days=[_planned_day(-1, "run")],
        workouts=[_workout(-1, "strength")],
    )

    result = await service.get_adherence("a1")

    assert result[0]["status"] == "swapped"


@pytest.mark.asyncio
async def test_rest_day_completed():
    service = _make_service(
        plan_days=[_planned_day(-1, "rest")],
        workouts=[],
    )

    result = await service.get_adherence("a1")

    assert result[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_no_plan_returns_empty():
    plan_cache = AsyncMock()
    plan_cache.get = AsyncMock(return_value=None)
    workout_repo = AsyncMock()
    service = PlanAdherenceService(plan_cache, workout_repo)

    result = await service.get_adherence("a1")

    assert result == []
