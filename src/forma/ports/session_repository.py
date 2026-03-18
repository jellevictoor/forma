"""Port: session persistence."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Session:
    token: str
    athlete_id: str
    expires_at: datetime


class SessionRepository(ABC):

    @abstractmethod
    async def get_by_token(self, token: str) -> Session | None:
        """Return the session if it exists and has not expired, else None."""

    @abstractmethod
    async def create(self, athlete_id: str, expires_at: datetime) -> Session:
        """Persist a new session and return it."""

    @abstractmethod
    async def delete(self, token: str) -> None:
        """Remove a session (logout)."""

    @abstractmethod
    async def delete_all_for_athlete(self, athlete_id: str) -> None:
        """Remove all sessions for an athlete."""
