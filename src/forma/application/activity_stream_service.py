"""Application service for lazy-fetching and caching GPS streams."""

import logging

from forma.ports.stream_repository import StreamRepository, WorkoutStreams

from forma.ports.strava import StravaClient
from forma.ports.workout_repository import WorkoutRepository
logger = logging.getLogger(__name__)


class ActivityStreamService:
    def __init__(
        self,
        workout_repo: WorkoutRepository,
        stream_repo: StreamRepository,
        strava_client: StravaClient,
    ) -> None:
        self._workouts = workout_repo
        self._streams = stream_repo
        self._strava = strava_client

    async def get_or_fetch(self, workout_id: str) -> WorkoutStreams | None:
        logger.info("streams requested for workout %s", workout_id)
        cached = await self._streams.get(workout_id)
        if cached:
            logger.info("stream cache hit for workout %s (%d points)", workout_id, len(cached.latlng))
            return cached

        workout = await self._workouts.get_workout(workout_id)
        if not workout:
            logger.warning("workout %s not found, cannot fetch streams", workout_id)
            return None
        if not workout.strava_id:
            logger.warning("workout %s has no strava_id, cannot fetch streams", workout_id)
            return None

        logger.info("fetching streams from Strava for workout %s (strava_id=%s)", workout_id, workout.strava_id)
        raw = await self._strava.get_activity_streams(workout.strava_id)
        if not raw or "latlng" not in raw:
            logger.warning("no latlng stream available for strava activity %s", workout.strava_id)
            return None

        streams = WorkoutStreams(
            latlng=raw["latlng"]["data"],
            time=raw["time"]["data"] if "time" in raw else [],
            velocity_smooth=raw["velocity_smooth"]["data"] if "velocity_smooth" in raw else [],
            heartrate=raw["heartrate"]["data"] if "heartrate" in raw else None,
        )
        logger.info("cached %d GPS points for workout %s (has_hr=%s)", len(streams.latlng), workout_id, streams.heartrate is not None)
        await self._streams.save(workout_id, streams)
        return streams
