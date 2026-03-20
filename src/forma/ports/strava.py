"""Port for Strava integration."""

from abc import ABC, abstractmethod
from datetime import datetime

from forma.domain.workout import Workout


class StravaRateLimitError(Exception):
    """Raised when Strava returns 429 Too Many Requests."""

    def __init__(self, retry_after: int = 900):
        self.retry_after = retry_after
        super().__init__(f"Strava rate limited, retry after {retry_after}s")


class StravaClient(ABC):
    """Abstract Strava API client."""

    @abstractmethod
    async def authenticate(self, authorization_code: str) -> dict:
        """Exchange authorization code for tokens."""
        ...

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> dict:
        """Refresh the access token."""
        ...

    @abstractmethod
    async def get_athlete(self) -> dict:
        """Get the authenticated athlete's profile."""
        ...

    @abstractmethod
    async def get_activities(
        self,
        after: datetime | None = None,
        before: datetime | None = None,
        page: int = 1,
        per_page: int = 30,
    ) -> list[dict]:
        """Get a list of activities."""
        ...

    @abstractmethod
    async def get_activity(self, activity_id: int) -> dict:
        """Get a specific activity with full details."""
        ...

    @abstractmethod
    async def get_activity_comments(self, activity_id: int) -> list[dict]:
        """Get comments on an activity."""
        ...

    @abstractmethod
    async def get_activity_streams(self, activity_id: int) -> dict:
        """Get GPS and metric streams for an activity keyed by type."""
        ...

    @abstractmethod
    def activity_to_workout(self, activity: dict, athlete_id: str) -> Workout:
        """Convert a Strava detail-endpoint activity to a Workout (detail_fetched=True)."""
        ...

    @abstractmethod
    def activity_to_workout_from_summary(self, activity: dict, athlete_id: str) -> Workout:
        """Convert a Strava list-endpoint summary to a Workout (detail_fetched=False)."""
        ...
