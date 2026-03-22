"""Tests for plan skip (not today) service."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest

from forma.application.plan_skip_service import PlanSkipService
from forma.domain.athlete import Athlete
from forma.ports.plan_cache_repository import CachedWeeklyPlan, PlannedDay


def _day(offset: int, sport: str = "run", intensity: str = "easy") -> PlannedDay:
    return PlannedDay(
        day=date(2026, 3, 23 + offset),
        workout_type=sport,
        intensity=intensity,
        duration_minutes=45,
        description="Test",
    )


def _make_service(plan_days, athlete=None) -> PlanSkipService:
    plan_cache = AsyncMock()
    plan_cache.get = AsyncMock(return_value=CachedWeeklyPlan(
        days=plan_days,
        rationale="Test",
        generated_at=datetime.now(tz=timezone.utc),
    ))
    plan_cache.save_days = AsyncMock()
    athlete_repo = AsyncMock()
    athlete_repo.get = AsyncMock(return_value=athlete or Athlete(id="a1", name="Test"))
    return PlanSkipService(plan_cache, athlete_repo)


@pytest.mark.asyncio
async def test_skip_swaps_with_rest_day():
    service = _make_service([_day(0, "run"), _day(1, "rest"), _day(2, "strength")])

    result = await service.skip_day("a1", date(2026, 3, 23))

    assert result["swapped_with"] == "2026-03-24"


@pytest.mark.asyncio
async def test_skip_persists_swapped_plan():
    service = _make_service([_day(0, "run"), _day(1, "rest")])

    await service.skip_day("a1", date(2026, 3, 23))

    service._plan_cache.save_days.assert_called_once()


@pytest.mark.asyncio
async def test_skip_returns_none_when_no_swap_possible():
    service = _make_service([_day(0, "run")])

    result = await service.skip_day("a1", date(2026, 3, 23))

    assert result["swapped_with"] is None


@pytest.mark.asyncio
async def test_skip_returns_updated_days():
    service = _make_service([_day(0, "run"), _day(1, "rest")])

    result = await service.skip_day("a1", date(2026, 3, 23))

    # After swap: Monday should be rest, Tuesday should be run
    assert result["days"][0]["workout_type"] == "rest"
    assert result["days"][1]["workout_type"] == "run"
