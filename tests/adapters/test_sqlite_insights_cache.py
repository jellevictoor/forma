"""Tests for SQLiteInsightsCache adapter."""

import pytest

from forma.adapters.sqlite_insights_cache import SQLiteInsightsCache
from forma.application.training_insights import TrainingInsights


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def cache(db_path):
    return SQLiteInsightsCache(db_path)


def _sample_insights(**overrides):
    defaults = dict(
        summary="Solid training block.",
        patterns=["Runs better rested", "Strength helps pace"],
        impact=["HR lower after rest", "Tempo improved"],
        recommendations=["Add more easy days", "Keep strength sessions short"],
        note_count=12,
    )
    defaults.update(overrides)
    return TrainingInsights(**defaults)


async def test_get_returns_none_when_not_cached(cache):
    result = await cache.get("athlete1", 2026)

    assert result is None


async def test_get_returns_cached_insights_after_save(cache):
    await cache.save("athlete1", 2026, _sample_insights())

    result = await cache.get("athlete1", 2026)

    assert result is not None


async def test_cached_insights_has_correct_summary(cache):
    await cache.save("athlete1", 2026, _sample_insights(summary="Great year."))

    result = await cache.get("athlete1", 2026)

    assert result.summary == "Great year."


async def test_cached_insights_has_correct_patterns(cache):
    await cache.save("athlete1", 2026, _sample_insights(patterns=["Pattern A", "Pattern B"]))

    result = await cache.get("athlete1", 2026)

    assert result.patterns == ["Pattern A", "Pattern B"]


async def test_cached_insights_has_correct_note_count(cache):
    await cache.save("athlete1", 2026, _sample_insights(note_count=7))

    result = await cache.get("athlete1", 2026)

    assert result.note_count == 7


async def test_cached_insights_has_year(cache):
    await cache.save("athlete1", 2026, _sample_insights())

    result = await cache.get("athlete1", 2026)

    assert result.year == 2026


async def test_save_overwrites_existing(cache):
    await cache.save("athlete1", 2026, _sample_insights(summary="First."))
    await cache.save("athlete1", 2026, _sample_insights(summary="Second."))

    result = await cache.get("athlete1", 2026)

    assert result.summary == "Second."


async def test_different_years_are_independent(cache):
    await cache.save("athlete1", 2025, _sample_insights(summary="2025 summary."))
    await cache.save("athlete1", 2026, _sample_insights(summary="2026 summary."))

    result_2025 = await cache.get("athlete1", 2025)
    result_2026 = await cache.get("athlete1", 2026)

    assert result_2025.summary == "2025 summary."
    assert result_2026.summary == "2026 summary."


async def test_different_athletes_are_independent(cache):
    await cache.save("athlete1", 2026, _sample_insights(summary="Athlete 1."))
    await cache.save("athlete2", 2026, _sample_insights(summary="Athlete 2."))

    result = await cache.get("athlete1", 2026)

    assert result.summary == "Athlete 1."
