"""Tests for WorkoutEnrichmentService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from forma.application.workout_enrichment import WorkoutEnrichmentService
from forma.domain.workout import Workout, WorkoutType
from datetime import datetime, timezone


def make_workout(detail_fetched: bool = False, strava_id: int = 123) -> Workout:
    return Workout(
        id="w1",
        strava_id=strava_id,
        athlete_id="athlete1",
        workout_type=WorkoutType.RUN,
        name="Morning Run",
        start_time=datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc),
        duration_seconds=3600,
        detail_fetched=detail_fetched,
    )


@pytest.fixture
def strava_client():
    client = AsyncMock()
    client.get_activity = AsyncMock(return_value={"id": 123})
    client.activity_to_workout = MagicMock(return_value=make_workout(detail_fetched=True))
    return client


@pytest.fixture
def workout_repo():
    repo = AsyncMock()
    repo.get_workout = AsyncMock(return_value=make_workout(detail_fetched=False))
    repo.save_workout = AsyncMock()
    return repo


async def test_returns_immediately_when_detail_already_fetched(strava_client, workout_repo):
    workout_repo.get_workout = AsyncMock(return_value=make_workout(detail_fetched=True))

    service = WorkoutEnrichmentService(strava_client, workout_repo)
    result = await service.ensure_detail("w1")

    assert result.detail_fetched is True
    strava_client.get_activity.assert_not_called()


async def test_fetches_detail_and_saves(strava_client, workout_repo):
    service = WorkoutEnrichmentService(strava_client, workout_repo)
    await service.ensure_detail("w1")

    strava_client.get_activity.assert_called_once_with(123)


async def test_preserves_id_during_enrichment(strava_client, workout_repo):
    enriched = make_workout(detail_fetched=True)
    enriched = enriched.model_copy(update={"id": "enriched-id"})
    strava_client.activity_to_workout = MagicMock(return_value=enriched)

    service = WorkoutEnrichmentService(strava_client, workout_repo)
    result = await service.ensure_detail("w1")

    assert result.id == "w1"


async def test_returns_none_when_workout_not_found(strava_client, workout_repo):
    workout_repo.get_workout = AsyncMock(return_value=None)

    service = WorkoutEnrichmentService(strava_client, workout_repo)
    result = await service.ensure_detail("w1")

    assert result is None
