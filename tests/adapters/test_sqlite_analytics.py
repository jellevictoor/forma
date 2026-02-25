"""Tests for SQLiteAnalyticsRepository."""

from datetime import datetime, timezone

import pytest

from fitness_coach.adapters.sqlite_analytics import SQLiteAnalyticsRepository
from fitness_coach.adapters.sqlite_storage import SQLiteStorage
from fitness_coach.domain.workout import Workout, WorkoutType


def make_workout(
    workout_id: str,
    athlete_id: str,
    workout_type: WorkoutType,
    start_time: datetime,
    duration_seconds: int = 3600,
    distance_meters: float | None = None,
    moving_time_seconds: int | None = None,
    average_heartrate: float | None = None,
) -> Workout:
    return Workout(
        id=workout_id,
        athlete_id=athlete_id,
        workout_type=workout_type,
        name="Test",
        start_time=start_time,
        duration_seconds=duration_seconds,
        moving_time_seconds=moving_time_seconds,
        distance_meters=distance_meters,
        average_heartrate=average_heartrate,
    )


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def storage(db_path):
    return SQLiteStorage(db_path)


@pytest.fixture
def analytics(db_path, storage):
    # storage fixture ensures DB schema is created
    return SQLiteAnalyticsRepository(db_path)


@pytest.mark.asyncio
async def test_weekly_volume_returns_empty_for_no_workouts(analytics):
    result = await analytics.weekly_volume("athlete1", None, 4)

    assert result == []


@pytest.mark.asyncio
async def test_weekly_volume_aggregates_runs(storage, analytics):
    athlete_id = "athlete1"
    await storage.save_workout(
        make_workout(
            "w1",
            athlete_id,
            WorkoutType.RUN,
            datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc),
            duration_seconds=3600,
            distance_meters=10000,
        )
    )
    await storage.save_workout(
        make_workout(
            "w2",
            athlete_id,
            WorkoutType.RUN,
            datetime(2026, 2, 17, 9, 0, tzinfo=timezone.utc),
            duration_seconds=1800,
            distance_meters=5000,
        )
    )

    result = await analytics.weekly_volume(athlete_id, "run", 2026)

    assert len(result) == 1
    assert result[0].total_distance_meters == 15000
    assert result[0].workout_count == 2


@pytest.mark.asyncio
async def test_weekly_volume_filters_by_workout_type(storage, analytics):
    athlete_id = "athlete1"
    await storage.save_workout(
        make_workout(
            "w1",
            athlete_id,
            WorkoutType.RUN,
            datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc),
            distance_meters=10000,
        )
    )
    await storage.save_workout(
        make_workout(
            "w2",
            athlete_id,
            WorkoutType.STRENGTH,
            datetime(2026, 2, 17, 9, 0, tzinfo=timezone.utc),
        )
    )

    result = await analytics.weekly_volume(athlete_id, "strength", 2026)

    assert len(result) == 1
    assert result[0].workout_count == 1


@pytest.mark.asyncio
async def test_sport_summaries_returns_one_row_per_type(storage, analytics):
    athlete_id = "athlete1"
    await storage.save_workout(
        make_workout(
            "w1",
            athlete_id,
            WorkoutType.RUN,
            datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc),
            distance_meters=10000,
        )
    )
    await storage.save_workout(
        make_workout(
            "w2",
            athlete_id,
            WorkoutType.STRENGTH,
            datetime(2026, 2, 17, 9, 0, tzinfo=timezone.utc),
        )
    )

    result = await analytics.sport_summaries(athlete_id, 2026)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_sport_summaries_totals_are_correct(storage, analytics):
    athlete_id = "athlete1"
    await storage.save_workout(
        make_workout(
            "w1",
            athlete_id,
            WorkoutType.RUN,
            datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc),
            distance_meters=10000,
            duration_seconds=3600,
        )
    )
    await storage.save_workout(
        make_workout(
            "w2",
            athlete_id,
            WorkoutType.RUN,
            datetime(2026, 2, 17, 9, 0, tzinfo=timezone.utc),
            distance_meters=5000,
            duration_seconds=1800,
        )
    )

    result = await analytics.sport_summaries(athlete_id, 2026)
    run_summary = next(s for s in result if s.workout_type == "run")

    assert run_summary.total_workouts == 2
    assert run_summary.total_distance_meters == 15000
    assert run_summary.total_duration_seconds == 5400


@pytest.mark.asyncio
async def test_personal_records_for_run_finds_best_effort(storage, analytics):
    athlete_id = "athlete1"
    # Slow 10k
    await storage.save_workout(
        make_workout(
            "w1",
            athlete_id,
            WorkoutType.RUN,
            datetime(2026, 2, 10, 9, 0, tzinfo=timezone.utc),
            distance_meters=10500,
            duration_seconds=3600,
            moving_time_seconds=3600,
        )
    )
    # Fast 10k
    await storage.save_workout(
        make_workout(
            "w2",
            athlete_id,
            WorkoutType.RUN,
            datetime(2026, 2, 17, 9, 0, tzinfo=timezone.utc),
            distance_meters=10500,
            duration_seconds=3000,
            moving_time_seconds=3000,
        )
    )

    result = await analytics.personal_records_for_run(athlete_id, [10000.0], 2026)

    assert result[0].workout_id == "w2"
    assert result[0].duration_seconds == 3000


@pytest.mark.asyncio
async def test_list_workouts_paginated_returns_correct_page(storage, analytics):
    athlete_id = "athlete1"
    for i in range(5):
        await storage.save_workout(
            make_workout(
                f"w{i}",
                athlete_id,
                WorkoutType.RUN,
                datetime(2026, 2, i + 1, 9, 0, tzinfo=timezone.utc),
            )
        )

    workouts, total = await analytics.list_workouts_paginated(athlete_id, "run", page=1, page_size=3, year=2026)

    assert total == 5
    assert len(workouts) == 3


@pytest.mark.asyncio
async def test_list_workouts_paginated_second_page(storage, analytics):
    athlete_id = "athlete1"
    for i in range(5):
        await storage.save_workout(
            make_workout(
                f"w{i}",
                athlete_id,
                WorkoutType.RUN,
                datetime(2026, 2, i + 1, 9, 0, tzinfo=timezone.utc),
            )
        )

    workouts, total = await analytics.list_workouts_paginated(athlete_id, "run", page=2, page_size=3, year=2026)

    assert len(workouts) == 2


@pytest.mark.asyncio
async def test_strength_frequency_returns_weekly_counts(storage, analytics):
    athlete_id = "athlete1"
    await storage.save_workout(
        make_workout(
            "w1",
            athlete_id,
            WorkoutType.STRENGTH,
            datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc),
        )
    )
    await storage.save_workout(
        make_workout(
            "w2",
            athlete_id,
            WorkoutType.STRENGTH,
            datetime(2026, 2, 17, 9, 0, tzinfo=timezone.utc),
        )
    )

    result = await analytics.strength_frequency(athlete_id, year=2026)

    assert len(result) == 1
    assert result[0]["count"] == 2


@pytest.mark.asyncio
async def test_climbing_sessions_returns_all_climbing_workouts(storage, analytics):
    athlete_id = "athlete1"
    await storage.save_workout(
        make_workout(
            "w1",
            athlete_id,
            WorkoutType.CLIMBING,
            datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc),
            duration_seconds=5400,
        )
    )
    await storage.save_workout(
        make_workout(
            "w2",
            athlete_id,
            WorkoutType.RUN,
            datetime(2026, 2, 17, 9, 0, tzinfo=timezone.utc),
        )
    )

    result = await analytics.climbing_sessions(athlete_id, 2026)

    assert len(result) == 1
    assert result[0]["id"] == "w1"


@pytest.mark.asyncio
async def test_pace_trend_returns_weekly_averages(storage, analytics):
    athlete_id = "athlete1"
    await storage.save_workout(
        make_workout(
            "w1",
            athlete_id,
            WorkoutType.RUN,
            datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc),
            distance_meters=10000,
            moving_time_seconds=3000,
        )
    )

    result = await analytics.pace_trend(athlete_id, "run", 2026)

    assert len(result) == 1
    assert result[0]["pace_min_per_km"] == pytest.approx(5.0, 0.01)


@pytest.mark.asyncio
async def test_sport_stats_for_month_returns_empty_for_no_workouts(analytics):
    result = await analytics.sport_stats_for_month("athlete1", 2026, 2)

    assert result == []


@pytest.mark.asyncio
async def test_sport_stats_for_month_counts_sessions(storage, analytics):
    athlete_id = "athlete1"
    await storage.save_workout(
        make_workout("w1", athlete_id, WorkoutType.RUN, datetime(2026, 2, 10, 9, 0, tzinfo=timezone.utc))
    )
    await storage.save_workout(
        make_workout("w2", athlete_id, WorkoutType.RUN, datetime(2026, 2, 17, 9, 0, tzinfo=timezone.utc))
    )

    result = await analytics.sport_stats_for_month(athlete_id, 2026, 2)
    run_stats = next(s for s in result if s["workout_type"] == "run")

    assert run_stats["sessions"] == 2


@pytest.mark.asyncio
async def test_sport_stats_for_month_excludes_other_months(storage, analytics):
    athlete_id = "athlete1"
    await storage.save_workout(
        make_workout("w1", athlete_id, WorkoutType.RUN, datetime(2026, 1, 31, 9, 0, tzinfo=timezone.utc))
    )
    await storage.save_workout(
        make_workout("w2", athlete_id, WorkoutType.RUN, datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc))
    )

    result = await analytics.sport_stats_for_month(athlete_id, 2026, 2)
    run_stats = next(s for s in result if s["workout_type"] == "run")

    assert run_stats["sessions"] == 1


@pytest.mark.asyncio
async def test_sport_stats_for_month_sums_distance(storage, analytics):
    athlete_id = "athlete1"
    await storage.save_workout(
        make_workout("w1", athlete_id, WorkoutType.RUN, datetime(2026, 2, 10, 9, 0, tzinfo=timezone.utc), distance_meters=5000)
    )
    await storage.save_workout(
        make_workout("w2", athlete_id, WorkoutType.RUN, datetime(2026, 2, 17, 9, 0, tzinfo=timezone.utc), distance_meters=10000)
    )

    result = await analytics.sport_stats_for_month(athlete_id, 2026, 2)
    run_stats = next(s for s in result if s["workout_type"] == "run")

    assert run_stats["distance_meters"] == 15000


@pytest.mark.asyncio
async def test_training_log_returns_empty_for_no_workouts(analytics):
    result = await analytics.training_log("athlete1", 2026)

    assert result == []


@pytest.mark.asyncio
async def test_training_log_returns_workout_fields(storage, analytics):
    athlete_id = "athlete1"
    await storage.save_workout(
        make_workout(
            "w1", athlete_id, WorkoutType.RUN,
            datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc),
            duration_seconds=3600,
            distance_meters=10000,
        )
    )

    result = await analytics.training_log(athlete_id, 2026)

    assert len(result) == 1
    assert result[0]["id"] == "w1"
    assert result[0]["date"] == "2026-02-16"
    assert result[0]["workout_type"] == "run"
    assert result[0]["duration_seconds"] == 3600


@pytest.mark.asyncio
async def test_training_log_filters_by_year(storage, analytics):
    athlete_id = "athlete1"
    await storage.save_workout(
        make_workout("w1", athlete_id, WorkoutType.RUN, datetime(2025, 12, 31, 9, 0, tzinfo=timezone.utc))
    )
    await storage.save_workout(
        make_workout("w2", athlete_id, WorkoutType.RUN, datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc))
    )

    result = await analytics.training_log(athlete_id, 2026)

    assert len(result) == 1
    assert result[0]["id"] == "w2"


@pytest.mark.asyncio
async def test_daily_effort_returns_empty_for_no_workouts(analytics):
    from datetime import date

    result = await analytics.daily_effort("athlete1", date(2026, 1, 1))

    assert result == []


@pytest.mark.asyncio
async def test_daily_effort_aggregates_two_workouts_on_same_day(storage, analytics):
    from datetime import date

    athlete_id = "athlete1"
    await storage.save_workout(
        make_workout("w1", athlete_id, WorkoutType.RUN, datetime(2026, 2, 16, 8, 0, tzinfo=timezone.utc), duration_seconds=1800)
    )
    await storage.save_workout(
        make_workout("w2", athlete_id, WorkoutType.STRENGTH, datetime(2026, 2, 16, 18, 0, tzinfo=timezone.utc), duration_seconds=1800)
    )

    result = await analytics.daily_effort(athlete_id, date(2026, 2, 1))

    assert len(result) == 1
    assert result[0]["date"] == "2026-02-16"


@pytest.mark.asyncio
async def test_daily_effort_uses_heart_rate_formula(storage, analytics):
    from datetime import date

    athlete_id = "athlete1"
    # 1 hour at 150 bpm should give effort = 100
    await storage.save_workout(
        make_workout(
            "w1", athlete_id, WorkoutType.RUN,
            datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc),
            duration_seconds=3600,
            average_heartrate=150.0,
        )
    )

    result = await analytics.daily_effort(athlete_id, date(2026, 2, 1))

    assert result[0]["effort"] == pytest.approx(100.0, rel=0.01)


@pytest.mark.asyncio
async def test_daily_effort_falls_back_to_duration_minutes(storage, analytics):
    from datetime import date

    athlete_id = "athlete1"
    # 60 minutes with no HR should give effort = 60
    await storage.save_workout(
        make_workout(
            "w1", athlete_id, WorkoutType.STRENGTH,
            datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc),
            duration_seconds=3600,
        )
    )

    result = await analytics.daily_effort(athlete_id, date(2026, 2, 1))

    assert result[0]["effort"] == pytest.approx(60.0, rel=0.01)
