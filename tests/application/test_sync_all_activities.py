"""Tests for FullStravaSync use case."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from forma.application.sync_all_activities import FullStravaSync
from forma.domain.workout import Workout, WorkoutType
from datetime import datetime, timezone


def make_workout(
    workout_id: str,
    strava_id: int,
    start_time: datetime | None = None,
) -> Workout:
    return Workout(
        id=workout_id,
        strava_id=strava_id,
        athlete_id="athlete1",
        workout_type=WorkoutType.RUN,
        name="Run",
        start_time=start_time or datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc),
        duration_seconds=3600,
    )


def make_activity(activity_id: int) -> dict:
    return {"id": activity_id, "type": "Run", "name": "Run"}


@pytest.fixture
def strava_client():
    client = AsyncMock()
    client.get_activities = AsyncMock(return_value=[])
    client.get_activity = AsyncMock(return_value={})
    client.activity_to_workout = MagicMock(return_value=make_workout("w1", 1))
    return client


@pytest.fixture
def workout_repo():
    repo = AsyncMock()
    repo.get_workout_by_strava_id = AsyncMock(return_value=None)
    repo.save_workout = AsyncMock()
    repo.get_oldest = AsyncMock(return_value=None)
    return repo


async def test_execute_returns_zero_when_no_activities(strava_client, workout_repo):
    strava_client.get_activities = AsyncMock(return_value=[])
    sync = FullStravaSync(strava_client, workout_repo)

    count = await sync.execute("athlete1")

    assert count == 0


async def test_execute_saves_new_activity(strava_client, workout_repo):
    strava_client.get_activities = AsyncMock(
        side_effect=[
            [make_activity(1)],
            [],
        ]
    )
    strava_client.get_activity = AsyncMock(return_value=make_activity(1))
    sync = FullStravaSync(strava_client, workout_repo)

    count = await sync.execute("athlete1")

    assert count == 1
    workout_repo.save_workout.assert_called_once()


async def test_execute_skips_existing_activity(strava_client, workout_repo):
    strava_client.get_activities = AsyncMock(
        side_effect=[
            [make_activity(1)],
            [],
        ]
    )
    workout_repo.get_workout_by_strava_id = AsyncMock(return_value=make_workout("w1", 1))
    sync = FullStravaSync(strava_client, workout_repo)

    count = await sync.execute("athlete1")

    assert count == 0
    workout_repo.save_workout.assert_not_called()


async def test_execute_paginates_until_empty_page(strava_client, workout_repo):
    strava_client.get_activities = AsyncMock(
        side_effect=[
            [make_activity(1), make_activity(2)],
            [make_activity(3)],
            [],
        ]
    )
    strava_client.get_activity = AsyncMock(
        side_effect=lambda aid: {"id": aid, "type": "Run", "name": "Run"}
    )
    strava_client.activity_to_workout = MagicMock(
        side_effect=lambda act, aid: make_workout(f"w{act['id']}", act["id"])
    )
    sync = FullStravaSync(strava_client, workout_repo)

    count = await sync.execute("athlete1")

    assert count == 3


async def test_backfill_fetches_older_activities_after_incremental_sync(
    strava_client, workout_repo
):
    """After incremental sync, a backfill pass fetches activities older than the oldest stored."""
    oldest = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    newest = datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc)

    workout_repo.get_recent = AsyncMock(
        return_value=[make_workout("w1", 1, start_time=newest)]
    )
    workout_repo.get_oldest = AsyncMock(
        return_value=make_workout("w1", 1, start_time=oldest)
    )

    # Incremental pass: nothing new. Backfill pass: one older activity, then empty.
    strava_client.get_activities = AsyncMock(
        side_effect=[
            [],              # incremental: nothing after newest
            [make_activity(2)],  # backfill: one older activity
            [],              # backfill: done
        ]
    )
    strava_client.get_activity = AsyncMock(return_value=make_activity(2))
    strava_client.activity_to_workout = MagicMock(
        return_value=make_workout("w2", 2, start_time=datetime(2025, 12, 1, tzinfo=timezone.utc))
    )

    sync = FullStravaSync(strava_client, workout_repo)
    count = await sync.execute("athlete1")

    assert count == 1


async def test_backfill_skips_when_no_stored_activities(strava_client, workout_repo):
    """No backfill pass when there are no stored activities (nothing to backfill from)."""
    workout_repo.get_recent = AsyncMock(return_value=[])
    workout_repo.get_oldest = AsyncMock(return_value=None)

    strava_client.get_activities = AsyncMock(return_value=[])

    sync = FullStravaSync(strava_client, workout_repo)
    count = await sync.execute("athlete1")

    assert count == 0


async def test_backfill_not_run_during_full_sync(strava_client, workout_repo):
    """Full sync already fetches everything — no separate backfill pass needed."""
    workout_repo.get_oldest = AsyncMock(return_value=None)

    strava_client.get_activities = AsyncMock(
        side_effect=[
            [make_activity(1)],
            [],
        ]
    )
    strava_client.get_activity = AsyncMock(return_value=make_activity(1))

    sync = FullStravaSync(strava_client, workout_repo)
    count = await sync.execute("athlete1", full=True)

    assert count == 1
    workout_repo.get_oldest.assert_not_called()
