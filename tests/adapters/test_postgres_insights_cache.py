"""Integration tests for PostgresInsightsCache."""

import pytest

from forma.adapters.postgres_insights_cache import PostgresInsightsCache
from forma.adapters.postgres_storage import PostgresStorage
from forma.domain.athlete import Athlete
from forma.ports.insights_cache_repository import CachedInsights


@pytest.fixture
async def athlete_id(pool):
    storage = PostgresStorage(pool)
    await storage.save(Athlete(id="athlete-insights", name="Insights Runner"))
    return "athlete-insights"


@pytest.fixture
def cache(pool):
    return PostgresInsightsCache(pool)


def _insights(year: int = 2025) -> CachedInsights:
    from datetime import datetime, timezone
    return CachedInsights(
        summary="Solid base building phase.",
        patterns=["Consistent mileage", "Good recovery"],
        impact=["Improved aerobic base"],
        recommendations=["Add one tempo run per week"],
        note_count=5,
        generated_at=datetime.now(tz=timezone.utc),
        year=year,
    )


async def test_get_returns_none_when_not_cached(cache):
    result = await cache.get("nonexistent", 2025)

    assert result is None


async def test_save_and_get_insights_summary(cache, athlete_id):
    await cache.save(athlete_id, 2025, _insights())

    result = await cache.get(athlete_id, 2025)

    assert result.summary == "Solid base building phase."


async def test_save_and_get_insights_patterns(cache, athlete_id):
    await cache.save(athlete_id, 2025, _insights())

    result = await cache.get(athlete_id, 2025)

    assert result.patterns == ["Consistent mileage", "Good recovery"]


async def test_save_and_get_insights_year(cache, athlete_id):
    await cache.save(athlete_id, 2025, _insights())

    result = await cache.get(athlete_id, 2025)

    assert result.year == 2025


async def test_insights_keyed_by_year(cache, athlete_id):
    await cache.save(athlete_id, 2024, _insights(2024))
    await cache.save(athlete_id, 2025, _insights(2025))

    result_2024 = await cache.get(athlete_id, 2024)

    assert result_2024.year == 2024


async def test_save_overwrites_existing_insights(cache, athlete_id):
    await cache.save(athlete_id, 2025, _insights())
    updated = _insights()
    updated.summary = "Updated summary."
    await cache.save(athlete_id, 2025, updated)

    result = await cache.get(athlete_id, 2025)

    assert result.summary == "Updated summary."
