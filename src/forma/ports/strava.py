"""Port for Strava integration."""

from abc import ABC, abstractmethod
from datetime import datetime

from forma.domain.workout import Workout


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
    def activity_to_workout(self, activity: dict, athlete_id: str) -> Workout:
        """Convert a Strava activity to a Workout domain entity."""
        ...
