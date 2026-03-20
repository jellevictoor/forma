"""On-demand detail enrichment for workouts saved from Strava summaries."""

import logging

from forma.domain.workout import Workout
from forma.ports.strava import StravaClient
from forma.ports.workout_repository import WorkoutRepository

logger = logging.getLogger(__name__)


class WorkoutEnrichmentService:
    """Fetches full Strava detail for a workout that was saved from a list summary."""

    def __init__(self, strava_client: StravaClient, workout_repo: WorkoutRepository) -> None:
        self._strava = strava_client
        self._workouts = workout_repo

    async def ensure_detail(self, workout_id: str) -> Workout | None:
        workout = await self._workouts.get_workout(workout_id)
        if workout is None:
            return None
        if workout.detail_fetched:
            return workout
        if workout.strava_id is None:
            return workout

        logger.info("fetching detail for workout %s (strava_id=%s)", workout_id, workout.strava_id)
        full_activity = await self._strava.get_activity(workout.strava_id)
        enriched = self._strava.activity_to_workout(full_activity, workout.athlete_id)

        enriched = enriched.model_copy(update={
            "id": workout.id,
            "mood": workout.mood,
            "sleep_quality": workout.sleep_quality,
        })

        await self._workouts.save_workout(enriched)
        return enriched
