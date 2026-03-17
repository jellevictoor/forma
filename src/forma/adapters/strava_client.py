"""Strava API client adapter."""

import asyncio
import uuid
from datetime import datetime

import httpx

from forma.domain.workout import PerceivedEffort, Workout, WorkoutType
from forma.ports.strava import StravaClient as StravaClientPort


STRAVA_TYPE_MAP = {
    "Run": WorkoutType.RUN,
    "Ride": WorkoutType.BIKE,
    "Swim": WorkoutType.SWIM,
    "Walk": WorkoutType.WALK,
    "Hike": WorkoutType.HIKE,
    "WeightTraining": WorkoutType.STRENGTH,
    "Workout": WorkoutType.STRENGTH,
    "Yoga": WorkoutType.YOGA,
    "RockClimbing": WorkoutType.CLIMBING,
}


class StravaClient(StravaClientPort):
    """HTTP client for Strava API."""

    BASE_URL = "https://www.strava.com/api/v3"
    AUTH_URL = "https://www.strava.com/oauth/token"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._client = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        await self._client.aclose()

    def _get_headers(self) -> dict:
        if not self._access_token:
            raise ValueError("No access token available. Please authenticate first.")
        return {"Authorization": f"Bearer {self._access_token}"}

    async def authenticate(self, authorization_code: str) -> dict:
        response = await self._client.post(
            self.AUTH_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": authorization_code,
                "grant_type": "authorization_code",
            },
        )
        response.raise_for_status()
        data = response.json()
        self._access_token = data["access_token"]
        self._refresh_token = data["refresh_token"]
        return data

    async def refresh_token(self, refresh_token: str | None = None) -> dict:
        token = refresh_token or self._refresh_token
        if not token:
            raise ValueError("No refresh token available.")

        response = await self._client.post(
            self.AUTH_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": token,
                "grant_type": "refresh_token",
            },
        )
        response.raise_for_status()
        data = response.json()
        self._access_token = data["access_token"]
        self._refresh_token = data["refresh_token"]
        return data

    async def get_athlete(self) -> dict:
        response = await self._client.get(
            f"{self.BASE_URL}/athlete",
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.json()

    RATE_LIMIT_RETRY_SECONDS = 30

    async def _throttle_if_needed(self, response: httpx.Response) -> None:
        usage_header = response.headers.get("X-ReadRateLimit-Usage", "")
        limit_header = response.headers.get("X-ReadRateLimit-Limit", "")
        if not usage_header or not limit_header:
            return
        short_usage = int(usage_header.split(",")[0])
        short_limit = int(limit_header.split(",")[0])
        if short_usage >= short_limit - 5:
            print(f"\nRate limit approaching, waiting {self.RATE_LIMIT_RETRY_SECONDS}s...")
            await asyncio.sleep(self.RATE_LIMIT_RETRY_SECONDS)

    async def _get_with_refresh(self, url: str, **kwargs) -> dict | list:
        response = await self._client.get(url, headers=self._get_headers(), **kwargs)
        if response.status_code == 401 and self._refresh_token:
            await self.refresh_token()
            response = await self._client.get(url, headers=self._get_headers(), **kwargs)
        while response.status_code == 429:
            print(f"\nRate limited (429). Retrying in {self.RATE_LIMIT_RETRY_SECONDS}s...")
            await asyncio.sleep(self.RATE_LIMIT_RETRY_SECONDS)
            response = await self._client.get(url, headers=self._get_headers(), **kwargs)
        response.raise_for_status()
        await self._throttle_if_needed(response)
        return response.json()

    async def get_activities(
        self,
        after: datetime | None = None,
        before: datetime | None = None,
        page: int = 1,
        per_page: int = 30,
    ) -> list[dict]:
        params: dict = {"page": page, "per_page": per_page}
        if after:
            params["after"] = int(after.timestamp())
        if before:
            params["before"] = int(before.timestamp())

        return await self._get_with_refresh(
            f"{self.BASE_URL}/athlete/activities", params=params
        )

    async def get_activity(self, activity_id: int) -> dict:
        return await self._get_with_refresh(f"{self.BASE_URL}/activities/{activity_id}")

    async def get_activity_comments(self, activity_id: int) -> list[dict]:
        response = await self._client.get(
            f"{self.BASE_URL}/activities/{activity_id}/comments",
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.json()

    def activity_to_workout(self, activity: dict, athlete_id: str) -> Workout:
        activity_type = activity.get("type", "Other")
        workout_type = STRAVA_TYPE_MAP.get(activity_type, WorkoutType.OTHER)

        start_time = datetime.fromisoformat(
            activity["start_date_local"].replace("Z", "+00:00")
        )

        private_note = activity.get("private_note", "") or ""

        return Workout(
            id=str(uuid.uuid4()),
            strava_id=activity["id"],
            athlete_id=athlete_id,
            workout_type=workout_type,
            name=activity.get("name", ""),
            description=activity.get("description", "") or "",
            start_time=start_time,
            duration_seconds=activity.get("elapsed_time", 0),
            moving_time_seconds=activity.get("moving_time"),
            distance_meters=activity.get("distance"),
            average_speed_mps=activity.get("average_speed"),
            max_speed_mps=activity.get("max_speed"),
            average_heartrate=activity.get("average_heartrate"),
            max_heartrate=activity.get("max_heartrate"),
            elevation_gain_meters=activity.get("total_elevation_gain"),
            private_note=private_note,
            perceived_effort=self._map_perceived_effort(activity.get("perceived_exertion")),
        )

    def _map_perceived_effort(self, strava_effort: int | None) -> PerceivedEffort | None:
        if strava_effort is None:
            return None
        if strava_effort <= 2:
            return PerceivedEffort.VERY_EASY
        elif strava_effort <= 4:
            return PerceivedEffort.EASY
        elif strava_effort <= 6:
            return PerceivedEffort.MODERATE
        elif strava_effort <= 8:
            return PerceivedEffort.HARD
        elif strava_effort <= 9:
            return PerceivedEffort.VERY_HARD
        else:
            return PerceivedEffort.MAXIMUM
