"""Strava sync use case — progressive sync with on-demand detail fetching."""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime

from forma.domain.athlete import SyncState
from forma.domain.plan_match import match_workout_to_plan
from forma.ports.athlete_repository import AthleteRepository
from forma.ports.plan_cache_repository import PlanCacheRepository
from forma.ports.strava import StravaClient, StravaRateLimitError
from forma.ports.workout_repository import WorkoutRepository

logger = logging.getLogger(__name__)

STRAVA_PAGE_SIZE = 200
RECENT_WEEKS = 12


@dataclass(frozen=True)
class SyncProgress:
    synced: int
    skipped: int
    activity_name: str
    phase: str = "new"  # "new" or "backfill"


# Optional callback: receives a SyncProgress after each activity.
OnProgress = Callable[[SyncProgress], Awaitable[None]]


class FullStravaSync:
    """Syncs Strava activity history into the local DB.

    Saves from list-endpoint summaries (no detail API call per activity).
    Detail is fetched on demand when the user views an activity.

    Incremental sync fetches new activities, then backfills older ones.
    Backfill saves a cursor so it can resume after rate limits or restarts.
    """

    def __init__(
        self,
        strava_client: StravaClient,
        workout_repo: WorkoutRepository,
        athlete_repo: AthleteRepository,
        plan_cache: PlanCacheRepository | None = None,
    ) -> None:
        self._strava = strava_client
        self._workouts = workout_repo
        self._athletes = athlete_repo
        self._plan_cache = plan_cache

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
        synced, skipped = await self._paginate(
            athlete_id, force_update, on_progress, after=after, phase="new",
        )

        # Update sync state after the forward pass
        if not full and not force_update:
            await self._update_sync_state(athlete_id, SyncState.UP_TO_DATE)
            backfill_synced, backfill_skipped = await self._backfill(
                athlete_id, on_progress,
            )
            synced += backfill_synced
            skipped += backfill_skipped

        logger.info("sync complete: %d saved, %d already up-to-date", synced, skipped)
        return synced

    async def _backfill(
        self,
        athlete_id: str,
        on_progress: OnProgress | None,
    ) -> tuple[int, int]:
        oldest = await self._workouts.get_oldest(athlete_id)
        if not oldest:
            return 0, 0

        logger.info("backfill pass: fetching activities before %s", oldest.start_time)
        await self._update_sync_state(
            athlete_id, SyncState.BACKFILL_IN_PROGRESS, cursor=oldest.start_time,
        )

        try:
            synced, skipped = await self._paginate(
                athlete_id, False, on_progress, before=oldest.start_time, phase="backfill",
            )
        except StravaRateLimitError:
            # Save cursor so we can resume later
            new_oldest = await self._workouts.get_oldest(athlete_id)
            cursor = new_oldest.start_time if new_oldest else oldest.start_time
            await self._update_sync_state(athlete_id, SyncState.BACKFILL_PAUSED, cursor=cursor)
            logger.warning("backfill paused due to rate limit for athlete %s", athlete_id)
            return 0, 0

        await self._update_sync_state(athlete_id, SyncState.COMPLETE)
        return synced, skipped

    async def resume_backfill(
        self,
        athlete_id: str,
        on_progress: OnProgress | None = None,
    ) -> int:
        """Resume a paused backfill from the stored cursor."""
        athlete = await self._athletes.get(athlete_id)
        if not athlete or athlete.sync_state not in (
            SyncState.BACKFILL_PAUSED, SyncState.BACKFILL_IN_PROGRESS, SyncState.UP_TO_DATE,
        ):
            return 0

        synced, _ = await self._backfill(athlete_id, on_progress)
        return synced

    async def _paginate(
        self,
        athlete_id: str,
        force_update: bool,
        on_progress: OnProgress | None,
        after: datetime | None = None,
        before: datetime | None = None,
        phase: str = "new",
    ) -> tuple[int, int]:
        synced = 0
        skipped = 0
        page = 1

        while True:
            activities = await self._strava.get_activities(
                after=after, before=before, page=page, per_page=STRAVA_PAGE_SIZE,
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
                        phase=phase,
                    ))

            page += 1

        return synced, skipped

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

        if force_update:
            full_activity = await self._strava.get_activity(activity["id"])
            workout = self._strava.activity_to_workout(full_activity, athlete_id)
        else:
            workout = self._strava.activity_to_workout_from_summary(activity, athlete_id)

        if existing:
            workout = workout.model_copy(update={
                "id": existing.id,
                "perceived_effort": existing.perceived_effort,
                "planned_description": existing.planned_description,
                "detail_fetched": existing.detail_fetched,
            })
            logger.debug("updated activity %s (%s)", activity["id"], workout.name)
        else:
            logger.debug("saved new activity %s (%s)", activity["id"], workout.name)

        # Match to plan if no planned description yet
        if not workout.planned_description and self._plan_cache:
            cached_plan = await self._plan_cache.get(athlete_id)
            if cached_plan:
                desc = match_workout_to_plan(workout, cached_plan.days)
                if desc:
                    workout = workout.model_copy(update={"planned_description": desc})
                    logger.info("matched %s to plan: %s", workout.name, desc[:60])

        await self._workouts.save_workout(workout)
        return 1

    async def _update_sync_state(
        self, athlete_id: str, state: SyncState, cursor: datetime | None = None,
    ) -> None:
        athlete = await self._athletes.get(athlete_id)
        if not athlete:
            return
        updates: dict = {"sync_state": state}
        if cursor is not None:
            updates["backfill_cursor"] = cursor
        await self._athletes.save(athlete.model_copy(update=updates))
