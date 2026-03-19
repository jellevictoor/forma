"""Full Strava sync use case — paginates all activity history with cursor support."""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime


from forma.ports.strava import StravaClient
from forma.ports.workout_repository import WorkoutRepository
logger = logging.getLogger(__name__)

STRAVA_PAGE_SIZE = 200


@dataclass(frozen=True)
class SyncProgress:
    synced: int
    skipped: int
    activity_name: str


# Optional callback: receives a SyncProgress after each activity.
OnProgress = Callable[[SyncProgress], Awaitable[None]]


class FullStravaSync:
    """Syncs Strava activity history into the local DB.

    Uses a cursor (latest stored activity start_time) so re-runs only
    fetch new activities. Pass full=True to ignore the cursor and
    re-fetch from the beginning. Pass force_update=True to overwrite
    already-stored activities with fresh data from Strava.
    """

    def __init__(self, strava_client: StravaClient, workout_repo: WorkoutRepository) -> None:
        self._strava = strava_client
        self._workouts = workout_repo

    async def execute(
        self,
        athlete_id: str,
        full: bool = False,
        force_update: bool = False,
        on_progress: OnProgress | None = None,
    ) -> int:
        mode = "force-full" if force_update else ("full" if full else "incremental")
        logger.info("starting %s sync for athlete %s", mode, athlete_id)

        after = None if full or force_update else await self._latest_stored_start_time(athlete_id)
        synced = 0
        skipped = 0
        page = 1

        while True:
            activities = await self._strava.get_activities(
                after=after, page=page, per_page=STRAVA_PAGE_SIZE
            )
            if not activities:
                break

            logger.debug("page %d: got %d activities", page, len(activities))
            for activity in activities:
                count = await self._sync_activity(activity, athlete_id, force_update)
                if count:
                    synced += count
                else:
                    skipped += 1

                if on_progress:
                    await on_progress(SyncProgress(
                        synced=synced,
                        skipped=skipped,
                        activity_name=activity.get("name", ""),
                    ))

            page += 1

        logger.info("sync complete: %d saved, %d already up-to-date", synced, skipped)
        return synced

    async def _latest_stored_start_time(self, athlete_id: str) -> datetime | None:
        recent = await self._workouts.get_recent(athlete_id, count=1)
        if not recent:
            return None
        return recent[0].start_time

    async def _sync_activity(
        self, activity: dict, athlete_id: str, force_update: bool = False
    ) -> int:
        existing = await self._workouts.get_workout_by_strava_id(activity["id"])

        if existing and not force_update:
            logger.debug("skipping existing activity %s (%s)", activity["id"], activity.get("name", ""))
            return 0

        full_activity = await self._strava.get_activity(activity["id"])
        workout = self._strava.activity_to_workout(full_activity, athlete_id)

        if existing:
            workout = workout.model_copy(update={
                "id": existing.id,
                "perceived_effort": existing.perceived_effort,
                "mood": existing.mood,
                "sleep_quality": existing.sleep_quality,
            })
            logger.debug("updated activity %s (%s)", activity["id"], workout.name)
        else:
            logger.debug("saved new activity %s (%s)", activity["id"], workout.name)

        await self._workouts.save_workout(workout)
        return 1
