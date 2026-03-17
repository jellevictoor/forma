"""Full Strava sync use case — paginates all activity history with cursor support."""

from datetime import datetime

from forma.ports.strava import StravaClient
from forma.ports.workout_repository import WorkoutRepository

STRAVA_PAGE_SIZE = 200


class FullStravaSync:
    """Syncs Strava activity history into the local DB.

    Uses a cursor (latest stored activity start_time) so re-runs only
    fetch new activities. Pass full=True to ignore the cursor and
    re-fetch from the beginning.
    """

    def __init__(self, strava_client: StravaClient, workout_repo: WorkoutRepository) -> None:
        self._strava = strava_client
        self._workouts = workout_repo

    async def execute(self, athlete_id: str, full: bool = False) -> int:
        after = None if full else await self._latest_stored_start_time(athlete_id)
        synced = 0
        page = 1

        while True:
            activities = await self._strava.get_activities(
                after=after, page=page, per_page=STRAVA_PAGE_SIZE
            )
            if not activities:
                break

            for activity in activities:
                count = await self._sync_activity(activity, athlete_id)
                synced += count

            page += 1

        return synced

    async def _latest_stored_start_time(self, athlete_id: str) -> datetime | None:
        recent = await self._workouts.get_recent(athlete_id, count=1)
        if not recent:
            return None
        return recent[0].start_time

    async def _sync_activity(self, activity: dict, athlete_id: str) -> int:
        existing = await self._workouts.get_workout_by_strava_id(activity["id"])
        if existing:
            return 0

        full_activity = await self._strava.get_activity(activity["id"])
        workout = self._strava.activity_to_workout(full_activity, athlete_id)
        await self._workouts.save_workout(workout)
        return 1
