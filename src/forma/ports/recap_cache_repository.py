"""Port for caching weekly recap output."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class WeeklyRecap:
    summary: str
    highlight: str
    form_note: str
    focus: list[str] = field(default_factory=list)


@dataclass
class CachedRecap:
    summary: str
    highlight: str
    form_note: str
    focus: list[str]
    generated_at: datetime
    latest_activity_at: datetime | None = field(default=None)
    is_stale: bool = field(default=False)


class RecapCacheRepository(ABC):
    """Stores and retrieves cached weekly recap results."""

    @abstractmethod
    async def get(self, athlete_id: str) -> CachedRecap | None:
        """Return the cached recap for an athlete, or None if not cached."""
        ...

    @abstractmethod
    async def save(
        self,
        athlete_id: str,
        recap: WeeklyRecap,
        latest_activity_at: datetime | None,
    ) -> None:
        """Persist a recap to the cache, recording generation time and latest activity."""
        ...
