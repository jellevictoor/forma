"""Tests for training alerts service."""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from forma.application.training_alerts import TrainingAlertsService
from forma.domain.workout import PerceivedEffort, Workout, WorkoutType
from forma.ports.workout_analytics_repository import WeeklyVolume


def _workout(days_ago: int, effort: PerceivedEffort | None = None, sport: str = "run") -> Workout:
    return Workout(
        id=f"w-{days_ago}",
        athlete_id="a1",
        workout_type=WorkoutType(sport),
        name=f"Workout {days_ago}d ago",
        start_time=datetime.now(tz=timezone.utc) - timedelta(days=days_ago),
        duration_seconds=3600,
        perceived_effort=effort,
    )


def _weekly_volume(weeks_ago: int, duration_hours: float) -> WeeklyVolume:
    return WeeklyVolume(
        week_start=date.today() - timedelta(weeks=weeks_ago),
        total_distance_meters=0,
        total_duration_seconds=int(duration_hours * 3600),
        workout_count=3,
        workout_type=None,
    )


def _make_service(workouts=None, volumes=None) -> TrainingAlertsService:
    repo = AsyncMock()
    repo.list_workouts_for_athlete = AsyncMock(return_value=workouts or [])
    analytics = AsyncMock()
    analytics.weekly_volume_for_range = AsyncMock(return_value=volumes or [])
    return TrainingAlertsService(repo, analytics)


@pytest.mark.asyncio
async def test_no_alerts_when_no_data():
    service = _make_service()

    alerts = await service.check("a1")

    assert alerts == []


@pytest.mark.asyncio
async def test_no_rest_day_alert_after_seven_consecutive_days():
    workouts = [_workout(i) for i in range(7)]
    service = _make_service(workouts=workouts)

    alerts = await service.check("a1")

    assert any(a.alert_type == "no_rest_day" for a in alerts)


@pytest.mark.asyncio
async def test_no_rest_day_alert_not_triggered_with_gap():
    workouts = [_workout(0), _workout(1), _workout(3)]
    service = _make_service(workouts=workouts)

    alerts = await service.check("a1")

    assert not any(a.alert_type == "no_rest_day" for a in alerts)


@pytest.mark.asyncio
async def test_volume_spike_alert():
    volumes = [
        _weekly_volume(4, 5.0),
        _weekly_volume(3, 5.0),
        _weekly_volume(2, 5.0),
        _weekly_volume(1, 5.0),
        _weekly_volume(0, 8.0),
    ]
    service = _make_service(volumes=volumes)

    alerts = await service.check("a1")

    assert any(a.alert_type == "volume_spike" for a in alerts)


@pytest.mark.asyncio
async def test_no_volume_spike_with_gradual_increase():
    volumes = [
        _weekly_volume(4, 5.0),
        _weekly_volume(3, 5.5),
        _weekly_volume(2, 6.0),
        _weekly_volume(1, 6.5),
        _weekly_volume(0, 7.0),
    ]
    service = _make_service(volumes=volumes)

    alerts = await service.check("a1")

    assert not any(a.alert_type == "volume_spike" for a in alerts)


@pytest.mark.asyncio
async def test_consecutive_hard_days_alert():
    workouts = [
        _workout(0, PerceivedEffort.HARD),
        _workout(1, PerceivedEffort.VERY_HARD),
        _workout(2, PerceivedEffort.MAXIMUM),
    ]
    service = _make_service(workouts=workouts)

    alerts = await service.check("a1")

    assert any(a.alert_type == "consecutive_hard_days" for a in alerts)


@pytest.mark.asyncio
async def test_no_consecutive_hard_alert_with_easy_day():
    workouts = [
        _workout(0, PerceivedEffort.HARD),
        _workout(1, PerceivedEffort.EASY),
        _workout(2, PerceivedEffort.HARD),
    ]
    service = _make_service(workouts=workouts)

    alerts = await service.check("a1")

    assert not any(a.alert_type == "consecutive_hard_days" for a in alerts)
