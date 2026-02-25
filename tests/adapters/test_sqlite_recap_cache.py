"""Tests for SQLiteRecapCache adapter."""

from datetime import datetime, timezone

import pytest

from fitness_coach.adapters.sqlite_recap_cache import SQLiteRecapCache
from fitness_coach.ports.recap_cache_repository import WeeklyRecap


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def cache(db_path):
    return SQLiteRecapCache(db_path)


async def test_get_returns_none_when_no_cache(cache):
    result = await cache.get("athlete1")

    assert result is None


async def test_get_returns_cached_recap_after_save(cache):
    recap = WeeklyRecap(summary="Solid week.", highlight="New PR.", form_note="Fresh.", focus=["More sleep"])
    await cache.save("athlete1", recap, latest_activity_at=None)

    result = await cache.get("athlete1")

    assert result is not None


async def test_cached_recap_has_correct_summary(cache):
    recap = WeeklyRecap(summary="Strong effort.", highlight="Pace improved.", form_note="Neutral.", focus=["Interval run"])
    await cache.save("athlete1", recap, latest_activity_at=None)

    result = await cache.get("athlete1")

    assert result.summary == "Strong effort."


async def test_cached_recap_has_correct_highlight(cache):
    recap = WeeklyRecap(summary="Solid.", highlight="New PR.", form_note="Fresh.", focus=[])
    await cache.save("athlete1", recap, latest_activity_at=None)

    result = await cache.get("athlete1")

    assert result.highlight == "New PR."


async def test_cached_recap_has_correct_focus_list(cache):
    recap = WeeklyRecap(summary="Good.", highlight="PR.", form_note="Tired.", focus=["Rest", "Easy run"])
    await cache.save("athlete1", recap, latest_activity_at=None)

    result = await cache.get("athlete1")

    assert result.focus == ["Rest", "Easy run"]


async def test_cached_recap_stores_latest_activity_at(cache):
    activity_time = datetime(2026, 2, 20, 10, 0, tzinfo=timezone.utc)
    recap = WeeklyRecap(summary="Good.", highlight="PR.", form_note="Fresh.", focus=[])
    await cache.save("athlete1", recap, latest_activity_at=activity_time)

    result = await cache.get("athlete1")

    assert result.latest_activity_at == activity_time


async def test_cached_recap_latest_activity_at_is_none_when_not_provided(cache):
    recap = WeeklyRecap(summary="Good.", highlight="PR.", form_note="Fresh.", focus=[])
    await cache.save("athlete1", recap, latest_activity_at=None)

    result = await cache.get("athlete1")

    assert result.latest_activity_at is None


async def test_save_overwrites_existing_cache(cache):
    first = WeeklyRecap(summary="First.", highlight="PR.", form_note="Fresh.", focus=[])
    second = WeeklyRecap(summary="Second.", highlight="Better PR.", form_note="Tired.", focus=[])
    await cache.save("athlete1", first, latest_activity_at=None)
    await cache.save("athlete1", second, latest_activity_at=None)

    result = await cache.get("athlete1")

    assert result.summary == "Second."


async def test_different_athletes_have_separate_caches(cache):
    recap_a = WeeklyRecap(summary="Athlete A.", highlight="PR.", form_note="Good.", focus=[])
    recap_b = WeeklyRecap(summary="Athlete B.", highlight="Base.", form_note="Tired.", focus=[])
    await cache.save("athlete_a", recap_a, latest_activity_at=None)
    await cache.save("athlete_b", recap_b, latest_activity_at=None)

    result_a = await cache.get("athlete_a")
    result_b = await cache.get("athlete_b")

    assert result_a.summary == "Athlete A."
    assert result_b.summary == "Athlete B."


async def test_get_none_for_unknown_athlete_after_other_athlete_cached(cache):
    recap = WeeklyRecap(summary="Good.", highlight="PR.", form_note="Fresh.", focus=[])
    await cache.save("athlete1", recap, latest_activity_at=None)

    result = await cache.get("athlete2")

    assert result is None
