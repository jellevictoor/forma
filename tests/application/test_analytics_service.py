"""Tests for AnalyticsService."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from forma.application.analytics_service import AnalyticsService, OverviewStats
from forma.ports.workout_analytics_repository import SportSummary, WeeklyVolume


def make_analytics_repo():
    repo = AsyncMock()
    repo.sport_summaries = AsyncMock(return_value=[])
    repo.weekly_volume = AsyncMock(return_value=[])
    repo.weekly_volume_for_range = AsyncMock(return_value=[])
    repo.pace_trend = AsyncMock(return_value=[])
    repo.personal_records_for_run = AsyncMock(return_value=[])
    repo.list_workouts_paginated = AsyncMock(return_value=([], 0))
    repo.strength_frequency = AsyncMock(return_value=[])
    repo.climbing_sessions = AsyncMock(return_value=[])
    repo.daily_effort = AsyncMock(return_value=[])
    repo.training_log = AsyncMock(return_value=[])
    repo.pace_trend_for_range = AsyncMock(return_value=[])
    repo.sport_stats_for_month = AsyncMock(return_value=[])
    return repo


def make_workout_repo():
    repo = AsyncMock()
    repo.get_recent = AsyncMock(return_value=[])
    return repo


async def test_overview_stats_returns_overview_stats_dataclass():
    analytics_repo = make_analytics_repo()
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.overview_stats("athlete1")

    assert isinstance(result, OverviewStats)


async def test_overview_stats_includes_sport_summaries():
    analytics_repo = make_analytics_repo()
    analytics_repo.sport_summaries = AsyncMock(
        return_value=[
            SportSummary("run", 10, 50000, 36000, date(2026, 2, 20)),
        ]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.overview_stats("athlete1")

    assert len(result.sport_summaries) == 1


async def test_weekly_volume_chart_data_delegates_to_repo():
    analytics_repo = make_analytics_repo()
    analytics_repo.weekly_volume = AsyncMock(
        return_value=[
            WeeklyVolume(date(2026, 2, 16), 10000, 3600, 2, "run"),
        ]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.weekly_volume_chart_data("athlete1", "run", year=2026)
    real_week = next(d for d in result if d["week_start"] == "2026-02-16")

    assert real_week["distance_km"] == pytest.approx(10.0)


async def test_weekly_volume_chart_data_includes_distance_km():
    analytics_repo = make_analytics_repo()
    analytics_repo.weekly_volume = AsyncMock(
        return_value=[
            WeeklyVolume(date(2026, 2, 16), 10000, 3600, 2, "run"),
        ]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.weekly_volume_chart_data("athlete1", "run", year=2026)
    real_week = next(d for d in result if d["week_start"] == "2026-02-16")

    assert real_week["distance_km"] == pytest.approx(10.0)


async def test_pace_trend_chart_data_returns_list():
    analytics_repo = make_analytics_repo()
    analytics_repo.pace_trend = AsyncMock(
        return_value=[{"week_start": "2026-02-16", "pace_min_per_km": 5.0}]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.pace_trend_chart_data("athlete1", "run")

    assert len(result) == 1


async def test_personal_records_calls_repo_with_standard_distances():
    analytics_repo = make_analytics_repo()
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    await service.personal_records("athlete1")

    call_args = analytics_repo.personal_records_for_run.call_args
    distances = call_args[0][1]
    assert 5000.0 in distances
    assert 10000.0 in distances
    assert 21097.0 in distances
    assert 42195.0 in distances


async def test_activities_page_returns_tuple_of_workouts_and_total():
    analytics_repo = make_analytics_repo()
    analytics_repo.list_workouts_paginated = AsyncMock(return_value=([], 0))
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    workouts, total = await service.activities_page("athlete1", "run", 1)

    assert total == 0
    assert workouts == []


async def test_strength_frequency_chart_data_returns_list():
    analytics_repo = make_analytics_repo()
    analytics_repo.strength_frequency = AsyncMock(
        return_value=[{"week_start": "2026-02-16", "count": 3}]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.strength_frequency_chart_data("athlete1")
    real_week = next(d for d in result if d["week_start"] == "2026-02-16")

    assert real_week["count"] == 3


async def test_climbing_history_returns_list():
    analytics_repo = make_analytics_repo()
    analytics_repo.climbing_sessions = AsyncMock(
        return_value=[{"id": "w1", "date": "2026-02-16", "duration_seconds": 5400}]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.climbing_history("athlete1")

    assert len(result) == 1


async def test_progress_comparison_returns_current_and_previous_month():
    analytics_repo = make_analytics_repo()
    analytics_repo.sport_stats_for_month = AsyncMock(return_value=[
        {"workout_type": "run", "sessions": 8, "distance_meters": 80000, "duration_seconds": 28800, "avg_pace_min_per_km": 6.0}
    ])
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.progress_comparison_data("athlete1")

    assert "current_month" in result
    assert "previous_month" in result
    assert "sports" in result


async def test_progress_comparison_sport_has_current_and_previous():
    analytics_repo = make_analytics_repo()
    analytics_repo.sport_stats_for_month = AsyncMock(return_value=[
        {"workout_type": "run", "sessions": 8, "distance_meters": 80000, "duration_seconds": 28800, "avg_pace_min_per_km": 6.0}
    ])
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.progress_comparison_data("athlete1")
    run_entry = next(s for s in result["sports"] if s["workout_type"] == "run")

    assert "current" in run_entry
    assert "previous" in run_entry


async def test_training_log_data_returns_list():
    analytics_repo = make_analytics_repo()
    analytics_repo.training_log = AsyncMock(return_value=[
        {"id": "w1", "date": "2026-02-16", "workout_type": "run", "duration_seconds": 3600, "distance_meters": 10000, "name": "Morning run"},
    ])
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.training_log_data("athlete1")

    assert isinstance(result, list)


async def test_training_log_data_delegates_to_repo():
    analytics_repo = make_analytics_repo()
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    await service.training_log_data("athlete1", year=2026)

    analytics_repo.training_log.assert_called_once_with("athlete1", 2026)


async def test_fitness_freshness_returns_list_of_dicts():
    analytics_repo = make_analytics_repo()
    analytics_repo.daily_effort = AsyncMock(return_value=[])
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.fitness_freshness_chart_data("athlete1")

    assert isinstance(result, list)


async def test_fitness_freshness_contains_expected_keys():
    analytics_repo = make_analytics_repo()
    analytics_repo.daily_effort = AsyncMock(
        return_value=[{"date": "2026-02-16", "effort": 80.0}]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.fitness_freshness_chart_data("athlete1", days=30)
    day = next(d for d in result if d["date"] == "2026-02-16")

    assert "fitness" in day
    assert "fatigue" in day
    assert "form" in day


async def test_fitness_freshness_form_equals_fitness_minus_fatigue():
    analytics_repo = make_analytics_repo()
    analytics_repo.daily_effort = AsyncMock(
        return_value=[{"date": "2026-02-16", "effort": 80.0}]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.fitness_freshness_chart_data("athlete1", days=30)
    day = next(d for d in result if d["date"] == "2026-02-16")

    assert day["form"] == pytest.approx(day["fitness"] - day["fatigue"], abs=0.2)


async def test_weekly_volume_fills_gaps_for_sport_specific_query():
    analytics_repo = make_analytics_repo()
    analytics_repo.weekly_volume = AsyncMock(
        return_value=[
            WeeklyVolume(date(2026, 1, 5), 10000, 3600, 2, "run"),
            WeeklyVolume(date(2026, 3, 2), 8000, 3000, 1, "run"),
        ]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.weekly_volume_chart_data("athlete1", "run", year=2026)

    assert len(result) > 2


async def test_weekly_volume_gap_filled_weeks_have_zero_values():
    analytics_repo = make_analytics_repo()
    analytics_repo.weekly_volume = AsyncMock(
        return_value=[
            WeeklyVolume(date(2026, 1, 5), 10000, 3600, 2, "run"),
        ]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.weekly_volume_chart_data("athlete1", "run", year=2026)
    gap_week = next(d for d in result if d["week_start"] != "2026-01-05")

    assert gap_week["distance_km"] == 0.0
    assert gap_week["duration_hours"] == 0.0
    assert gap_week["workout_count"] == 0


async def test_weekly_volume_preserves_real_data_in_gap_fill():
    analytics_repo = make_analytics_repo()
    analytics_repo.weekly_volume = AsyncMock(
        return_value=[
            WeeklyVolume(date(2026, 2, 16), 10000, 3600, 2, "run"),
        ]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.weekly_volume_chart_data("athlete1", "run", year=2026)
    real_week = next(d for d in result if d["week_start"] == "2026-02-16")

    assert real_week["distance_km"] == pytest.approx(10.0)


async def test_weekly_volume_no_gap_fill_without_workout_type():
    analytics_repo = make_analytics_repo()
    analytics_repo.weekly_volume = AsyncMock(
        return_value=[
            WeeklyVolume(date(2026, 1, 5), 10000, 3600, 2, "run"),
            WeeklyVolume(date(2026, 1, 5), 5000, 1800, 1, "strength"),
        ]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.weekly_volume_chart_data("athlete1", None, year=2026)

    assert len(result) == 2


async def test_strength_frequency_fills_gaps():
    analytics_repo = make_analytics_repo()
    analytics_repo.strength_frequency = AsyncMock(
        return_value=[
            {"week_start": "2026-01-05", "count": 3},
            {"week_start": "2026-03-02", "count": 2},
        ]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.strength_frequency_chart_data("athlete1", year=2026)

    assert len(result) > 2


async def test_strength_frequency_gap_weeks_have_zero_count():
    analytics_repo = make_analytics_repo()
    analytics_repo.strength_frequency = AsyncMock(
        return_value=[
            {"week_start": "2026-01-05", "count": 3},
        ]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.strength_frequency_chart_data("athlete1", year=2026)
    gap_week = next(d for d in result if d["week_start"] != "2026-01-05")

    assert gap_week["count"] == 0


async def test_weekly_volume_gap_fill_covers_full_year():
    analytics_repo = make_analytics_repo()
    analytics_repo.weekly_volume = AsyncMock(
        return_value=[
            WeeklyVolume(date(2026, 6, 15), 10000, 3600, 2, "run"),
        ]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.weekly_volume_chart_data("athlete1", "run", year=2026)

    assert len(result) >= 52


async def test_unified_volume_returns_one_row_per_week():
    analytics_repo = make_analytics_repo()
    analytics_repo.weekly_volume_for_range = AsyncMock(
        return_value=[
            WeeklyVolume(date(2026, 1, 5), 10000, 3600, 2, "run"),
            WeeklyVolume(date(2026, 1, 5), 0, 1800, 1, "strength"),
        ]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.unified_volume_chart_data("athlete1", months=3)

    assert all("run_hours" in d and "strength_hours" in d and "climbing_hours" in d for d in result)


async def test_unified_volume_pivots_sports_into_columns():
    analytics_repo = make_analytics_repo()
    analytics_repo.weekly_volume_for_range = AsyncMock(
        return_value=[
            WeeklyVolume(date(2026, 2, 2), 10000, 7200, 2, "run"),
            WeeklyVolume(date(2026, 2, 2), 0, 3600, 1, "strength"),
        ]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.unified_volume_chart_data("athlete1", months=3)
    week = next(d for d in result if d["week_start"] == "2026-02-02")

    assert week["run_hours"] == pytest.approx(2.0)


async def test_unified_volume_missing_sport_defaults_to_zero():
    analytics_repo = make_analytics_repo()
    analytics_repo.weekly_volume_for_range = AsyncMock(
        return_value=[
            WeeklyVolume(date(2026, 2, 2), 10000, 3600, 2, "run"),
        ]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.unified_volume_chart_data("athlete1", months=3)
    week = next(d for d in result if d["week_start"] == "2026-02-02")

    assert week["climbing_hours"] == 0.0


async def test_unified_volume_gap_fills_weeks_in_range():
    analytics_repo = make_analytics_repo()
    analytics_repo.weekly_volume_for_range = AsyncMock(
        return_value=[
            WeeklyVolume(date(2026, 2, 2), 10000, 3600, 2, "run"),
        ]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.unified_volume_chart_data("athlete1", months=3)

    assert len(result) >= 12


async def test_unified_volume_clamps_months_to_valid_range():
    analytics_repo = make_analytics_repo()
    analytics_repo.weekly_volume_for_range = AsyncMock(return_value=[])
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.unified_volume_chart_data("athlete1", months=99)

    assert len(result) >= 12
    assert len(result) <= 14


async def test_weekly_volume_with_months_uses_range_repo():
    analytics_repo = make_analytics_repo()
    analytics_repo.weekly_volume_for_range = AsyncMock(
        return_value=[
            WeeklyVolume(date(2026, 2, 2), 10000, 3600, 2, "run"),
        ]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.weekly_volume_chart_data("athlete1", "run", months=3)

    assert analytics_repo.weekly_volume_for_range.called


async def test_weekly_volume_with_months_gap_fills_range():
    analytics_repo = make_analytics_repo()
    analytics_repo.weekly_volume_for_range = AsyncMock(
        return_value=[
            WeeklyVolume(date(2026, 2, 2), 10000, 3600, 2, "run"),
        ]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.weekly_volume_chart_data("athlete1", "run", months=3)

    assert len(result) >= 12


async def test_pace_trend_for_range_returns_list():
    analytics_repo = make_analytics_repo()
    analytics_repo.pace_trend_for_range = AsyncMock(
        return_value=[{"week_start": "2026-02-02", "pace_min_per_km": 5.5}]
    )
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    result = await service.pace_trend_chart_data("athlete1", "run", months=3)

    assert len(result) == 1


async def test_pace_trend_for_range_calls_range_repo():
    analytics_repo = make_analytics_repo()
    analytics_repo.pace_trend_for_range = AsyncMock(return_value=[])
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    await service.pace_trend_chart_data("athlete1", "run", months=6)

    assert analytics_repo.pace_trend_for_range.called


async def test_range_queries_include_today():
    analytics_repo = make_analytics_repo()
    analytics_repo.weekly_volume_for_range = AsyncMock(return_value=[])
    workout_repo = make_workout_repo()
    service = AnalyticsService(analytics_repo, workout_repo)

    await service.unified_volume_chart_data("athlete1", months=3)

    call_args = analytics_repo.weekly_volume_for_range.call_args[0]
    until_date = call_args[2]

    assert until_date > date.today()
