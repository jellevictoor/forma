"""Tests for WeeklyRecapService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch


from forma.application.weekly_recap import WeeklyRecapService
from forma.domain.workout import Workout, WorkoutType
from forma.ports.recap_cache_repository import CachedRecap, WeeklyRecap


def make_workout(workout_id, workout_type, days_ago, duration_seconds=3600, distance_meters=None):
    start = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    return Workout(
        id=workout_id,
        athlete_id="athlete1",
        workout_type=workout_type,
        name="Test",
        start_time=start,
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
    )


def make_deps():
    analytics_repo = AsyncMock()
    analytics_repo.daily_effort = AsyncMock(return_value=[])
    workout_repo = AsyncMock()
    workout_repo.get_recent = AsyncMock(return_value=[])
    cache_repo = AsyncMock()
    cache_repo.get = AsyncMock(return_value=None)
    cache_repo.save = AsyncMock()
    return analytics_repo, workout_repo, cache_repo


async def test_generate_and_cache_returns_cached_recap():
    analytics_repo, workout_repo, cache_repo = make_deps()
    service = WeeklyRecapService(analytics_repo, workout_repo, "fake-key", cache_repo)

    with patch.object(service, "_call_gemini", return_value=WeeklyRecap(
        summary="Solid week.", highlight="New distance high.", form_note="Fresh.", focus=["Add tempo run"]
    )):
        result = await service.generate_and_cache("athlete1")

    assert isinstance(result, CachedRecap)


async def test_generate_and_cache_no_workouts_returns_cached_recap():
    analytics_repo, workout_repo, cache_repo = make_deps()
    service = WeeklyRecapService(analytics_repo, workout_repo, "fake-key", cache_repo)

    result = await service.generate_and_cache("athlete1")

    assert result.summary != ""
    assert result.focus == []


async def test_generate_and_cache_does_not_call_gemini_when_no_workouts():
    analytics_repo, workout_repo, cache_repo = make_deps()
    service = WeeklyRecapService(analytics_repo, workout_repo, "fake-key", cache_repo)

    with patch.object(service, "_call_gemini") as mock_gemini:
        await service.generate_and_cache("athlete1")

    mock_gemini.assert_not_called()


async def test_generate_and_cache_calls_gemini_when_workouts_exist():
    analytics_repo, workout_repo, cache_repo = make_deps()
    workout_repo.get_recent = AsyncMock(return_value=[
        make_workout("w1", WorkoutType.RUN, days_ago=2, distance_meters=10000),
    ])
    service = WeeklyRecapService(analytics_repo, workout_repo, "fake-key", cache_repo)

    with patch.object(service, "_call_gemini", return_value=WeeklyRecap(
        summary="Good week.", highlight="PR pace.", form_note="Tired.", focus=["Rest day"]
    )) as mock_gemini:
        await service.generate_and_cache("athlete1")

    mock_gemini.assert_called_once()


async def test_generate_and_cache_saves_to_cache():
    analytics_repo, workout_repo, cache_repo = make_deps()
    service = WeeklyRecapService(analytics_repo, workout_repo, "fake-key", cache_repo)

    with patch.object(service, "_call_gemini", return_value=WeeklyRecap(
        summary="Good.", highlight="PR.", form_note="Fresh.", focus=[]
    )):
        await service.generate_and_cache("athlete1")

    cache_repo.save.assert_called_once()


async def test_get_cached_returns_none_when_no_cache():
    analytics_repo, workout_repo, cache_repo = make_deps()
    service = WeeklyRecapService(analytics_repo, workout_repo, "fake-key", cache_repo)

    result = await service.get_cached("athlete1")

    assert result is None


async def test_get_cached_returns_cached_recap():
    analytics_repo, workout_repo, cache_repo = make_deps()
    cached = CachedRecap(
        summary="Cached.", highlight="PR.", form_note="Good.", focus=[],
        generated_at=datetime.now(tz=timezone.utc),
    )
    cache_repo.get = AsyncMock(return_value=cached)
    service = WeeklyRecapService(analytics_repo, workout_repo, "fake-key", cache_repo)

    result = await service.get_cached("athlete1")

    assert result is cached


async def test_get_cached_does_not_call_gemini():
    analytics_repo, workout_repo, cache_repo = make_deps()
    service = WeeklyRecapService(analytics_repo, workout_repo, "fake-key", cache_repo)

    with patch.object(service, "_call_gemini") as mock_gemini:
        await service.get_cached("athlete1")

    mock_gemini.assert_not_called()
