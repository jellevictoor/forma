"""Tests for FullStravaSync use case."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from forma.application.sync_all_activities import FullStravaSync
from forma.domain.athlete import Athlete, SyncState
from forma.domain.workout import Workout, WorkoutType
from forma.ports.strava import StravaRateLimitError
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


def make_athlete(sync_state: SyncState = SyncState.NEVER_SYNCED) -> Athlete:
    return Athlete(id="athlete1", name="Test", sync_state=sync_state)


@pytest.fixture
def strava_client():
    client = AsyncMock()
    client.get_activities = AsyncMock(return_value=[])
    client.get_activity = AsyncMock(return_value={})
    client.activity_to_workout_from_summary = MagicMock(return_value=make_workout("w1", 1))
    client.activity_to_workout = MagicMock(return_value=make_workout("w1", 1))
    return client


@pytest.fixture
def workout_repo():
    repo = AsyncMock()
    repo.get_workout_by_strava_id = AsyncMock(return_value=None)
    repo.save_workout = AsyncMock()
    repo.get_oldest = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def athlete_repo():
    repo = AsyncMock()
    repo.get = AsyncMock(return_value=make_athlete())
    repo.save = AsyncMock()
    return repo


async def test_execute_returns_zero_when_no_activities(strava_client, workout_repo, athlete_repo):
    strava_client.get_activities = AsyncMock(return_value=[])
    sync = FullStravaSync(strava_client, workout_repo, athlete_repo)

    count = await sync.execute("athlete1")

    assert count == 0


async def test_execute_saves_new_activity_from_summary(strava_client, workout_repo, athlete_repo):
    strava_client.get_activities = AsyncMock(
        side_effect=[
            [make_activity(1)],
            [],
        ]
    )
    sync = FullStravaSync(strava_client, workout_repo, athlete_repo)

    count = await sync.execute("athlete1")

    assert count == 1


async def test_execute_does_not_call_detail_endpoint(strava_client, workout_repo, athlete_repo):
    strava_client.get_activities = AsyncMock(
        side_effect=[
            [make_activity(1)],
            [],
        ]
    )
    sync = FullStravaSync(strava_client, workout_repo, athlete_repo)

    await sync.execute("athlete1")

    strava_client.get_activity.assert_not_called()


async def test_execute_uses_summary_conversion(strava_client, workout_repo, athlete_repo):
    strava_client.get_activities = AsyncMock(
        side_effect=[
            [make_activity(1)],
            [],
        ]
    )
    sync = FullStravaSync(strava_client, workout_repo, athlete_repo)

    await sync.execute("athlete1")

    strava_client.activity_to_workout_from_summary.assert_called_once()


async def test_force_update_calls_detail_endpoint(strava_client, workout_repo, athlete_repo):
    strava_client.get_activities = AsyncMock(
        side_effect=[
            [make_activity(1)],
            [],
        ]
    )
    strava_client.get_activity = AsyncMock(return_value=make_activity(1))
    sync = FullStravaSync(strava_client, workout_repo, athlete_repo)

    await sync.execute("athlete1", full=True, force_update=True)

    strava_client.get_activity.assert_called_once()


async def test_execute_skips_existing_activity(strava_client, workout_repo, athlete_repo):
    strava_client.get_activities = AsyncMock(
        side_effect=[
            [make_activity(1)],
            [],
        ]
    )
    workout_repo.get_workout_by_strava_id = AsyncMock(return_value=make_workout("w1", 1))
    sync = FullStravaSync(strava_client, workout_repo, athlete_repo)

    count = await sync.execute("athlete1")

    assert count == 0


async def test_execute_paginates_until_empty_page(strava_client, workout_repo, athlete_repo):
    strava_client.get_activities = AsyncMock(
        side_effect=[
            [make_activity(1), make_activity(2)],
            [make_activity(3)],
            [],
        ]
    )
    strava_client.activity_to_workout_from_summary = MagicMock(
        side_effect=lambda act, aid: make_workout(f"w{act['id']}", act["id"])
    )
    sync = FullStravaSync(strava_client, workout_repo, athlete_repo)

    count = await sync.execute("athlete1")

    assert count == 3


async def test_backfill_fetches_older_activities(strava_client, workout_repo, athlete_repo):
    oldest = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    newest = datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc)

    workout_repo.get_recent = AsyncMock(
        return_value=[make_workout("w1", 1, start_time=newest)]
    )
    workout_repo.get_oldest = AsyncMock(
        return_value=make_workout("w1", 1, start_time=oldest)
    )

    strava_client.get_activities = AsyncMock(
        side_effect=[
            [],              # incremental: nothing after newest
            [make_activity(2)],  # backfill: one older activity
            [],              # backfill: done
        ]
    )
    strava_client.activity_to_workout_from_summary = MagicMock(
        return_value=make_workout("w2", 2, start_time=datetime(2025, 12, 1, tzinfo=timezone.utc))
    )

    sync = FullStravaSync(strava_client, workout_repo, athlete_repo)
    count = await sync.execute("athlete1")

    assert count == 1


async def test_backfill_skips_when_no_stored_activities(strava_client, workout_repo, athlete_repo):
    workout_repo.get_recent = AsyncMock(return_value=[])
    workout_repo.get_oldest = AsyncMock(return_value=None)

    strava_client.get_activities = AsyncMock(return_value=[])

    sync = FullStravaSync(strava_client, workout_repo, athlete_repo)
    count = await sync.execute("athlete1")

    assert count == 0


async def test_backfill_not_run_during_full_sync(strava_client, workout_repo, athlete_repo):
    workout_repo.get_oldest = AsyncMock(return_value=None)

    strava_client.get_activities = AsyncMock(
        side_effect=[
            [make_activity(1)],
            [],
        ]
    )

    sync = FullStravaSync(strava_client, workout_repo, athlete_repo)
    count = await sync.execute("athlete1", full=True)

    assert count == 1


async def test_sync_state_set_to_complete_after_backfill(strava_client, workout_repo, athlete_repo):
    workout_repo.get_oldest = AsyncMock(return_value=make_workout("w1", 1))

    strava_client.get_activities = AsyncMock(return_value=[])

    sync = FullStravaSync(strava_client, workout_repo, athlete_repo)
    await sync.execute("athlete1")

    saved_athletes = [call.args[0] for call in athlete_repo.save.call_args_list]
    assert saved_athletes[-1].sync_state == SyncState.COMPLETE


async def test_backfill_paused_on_rate_limit(strava_client, workout_repo, athlete_repo):
    oldest = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
    workout_repo.get_oldest = AsyncMock(
        return_value=make_workout("w1", 1, start_time=oldest)
    )

    strava_client.get_activities = AsyncMock(
        side_effect=[
            [],  # incremental: nothing new
            StravaRateLimitError(retry_after=900),  # backfill: rate limited
        ]
    )

    sync = FullStravaSync(strava_client, workout_repo, athlete_repo)
    await sync.execute("athlete1")

    saved_athletes = [call.args[0] for call in athlete_repo.save.call_args_list]
    assert saved_athletes[-1].sync_state == SyncState.BACKFILL_PAUSED


async def test_resume_backfill_returns_zero_when_not_paused(strava_client, workout_repo, athlete_repo):
    athlete_repo.get = AsyncMock(return_value=make_athlete(SyncState.COMPLETE))

    sync = FullStravaSync(strava_client, workout_repo, athlete_repo)
    count = await sync.resume_backfill("athlete1")

    assert count == 0
