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
            gps_pts = len(cached.latlng) if cached.latlng else 0
            logger.info("stream cache hit for workout %s (%d gps points)", workout_id, gps_pts)
            return cached

        workout = await self._workouts.get_workout(workout_id)
        if not workout:
            logger.warning("workout %s not found, cannot fetch streams", workout_id)
            return None
        if not workout.strava_id:
            logger.warning("workout %s has no strava_id, cannot fetch streams", workout_id)
            return None

        logger.info("fetching streams from Strava for workout %s (strava_id=%s)", workout_id, workout.strava_id)
        try:
            raw = await self._strava.get_activity_streams(workout.strava_id)
        except Exception:
            logger.warning("failed to fetch streams from Strava for activity %s", workout.strava_id)
            return None
        if not raw:
            return None

        has_latlng = "latlng" in raw
        has_heartrate = "heartrate" in raw
        if not has_latlng and not has_heartrate:
            logger.warning("no stream data available for strava activity %s", workout.strava_id)
            return None

        streams = WorkoutStreams(
            latlng=raw["latlng"]["data"] if has_latlng else None,
            time=raw["time"]["data"] if "time" in raw else [],
            velocity_smooth=raw["velocity_smooth"]["data"] if "velocity_smooth" in raw else [],
            heartrate=raw["heartrate"]["data"] if has_heartrate else None,
        )
        gps_pts = len(streams.latlng) if streams.latlng else 0
        logger.info("cached streams for workout %s (gps=%d pts, has_hr=%s)", workout_id, gps_pts, has_heartrate)
        await self._streams.save(workout_id, streams)
        return streams
