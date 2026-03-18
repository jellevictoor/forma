"""Integration tests for PostgresRecapCache."""

from datetime import datetime, timezone

import pytest

from forma.adapters.postgres_recap_cache import PostgresRecapCache
from forma.adapters.postgres_storage import PostgresStorage
from forma.domain.athlete import Athlete
from forma.ports.recap_cache_repository import WeeklyRecap


@pytest.fixture
async def athlete_id(pool):
    storage = PostgresStorage(pool)
    await storage.save(Athlete(id="athlete-recap", name="Recap Runner"))
    return "athlete-recap"


@pytest.fixture
def cache(pool):
    return PostgresRecapCache(pool)


def _recap() -> WeeklyRecap:
    return WeeklyRecap(
        summary="Good week of training.",
        highlight="Long run on Saturday.",
        form_note="HR slightly elevated.",
        focus=["Easy pace", "Sleep"],
    )


async def test_get_returns_none_when_not_cached(cache):
    result = await cache.get("nonexistent")

    assert result is None


async def test_save_and_get_recap_summary(cache, athlete_id):
    await cache.save(athlete_id, _recap(), latest_activity_at=None)

    result = await cache.get(athlete_id)

    assert result.summary == "Good week of training."


async def test_save_and_get_recap_focus_list(cache, athlete_id):
    await cache.save(athlete_id, _recap(), latest_activity_at=None)

    result = await cache.get(athlete_id)

    assert result.focus == ["Easy pace", "Sleep"]


async def test_save_and_get_recap_latest_activity_at(cache, athlete_id):
    latest = datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc)
    await cache.save(athlete_id, _recap(), latest_activity_at=latest)

    result = await cache.get(athlete_id)

    assert result.latest_activity_at is not None


async def test_save_overwrites_existing_recap(cache, athlete_id):
    await cache.save(athlete_id, _recap(), latest_activity_at=None)
    updated = WeeklyRecap(
        summary="Updated summary.",
        highlight="New highlight.",
        form_note="Form note.",
        focus=["Rest"],
    )
    await cache.save(athlete_id, updated, latest_activity_at=None)

    result = await cache.get(athlete_id)

    assert result.summary == "Updated summary."
