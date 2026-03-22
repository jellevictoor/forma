"""Port for caching weekly workout plan output."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class PlannedDay:
    """A single day in the generated weekly plan."""

    day: date
    workout_type: str
    intensity: str
    duration_minutes: int
    description: str
    exercises: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class WeeklyPlan:
    """A generated 7-day workout plan."""

    days: list[PlannedDay]
    rationale: str
    generated_at: datetime


@dataclass
class CachedWeeklyPlan:
    """A cached weekly plan with staleness metadata."""

    days: list[PlannedDay]
    rationale: str
    generated_at: datetime
    latest_activity_at: datetime | None = field(default=None)
    is_stale: bool = field(default=False)


class PlanCacheRepository(ABC):
    """Stores and retrieves cached weekly plan results."""

    @abstractmethod
    async def get(self, athlete_id: str) -> CachedWeeklyPlan | None:
        """Return the cached plan for an athlete, or None if not cached."""
        ...

    @abstractmethod
    async def save(
        self,
        athlete_id: str,
        plan: WeeklyPlan,
        latest_activity_at: datetime | None,
    ) -> None:
        """Persist a plan to the cache, recording generation time and latest activity."""
        ...

    @abstractmethod
    async def update_day_exercises(self, athlete_id: str, day: date, exercises: dict[str, list[str]]) -> None:
        """Update the exercises for a specific day in the cached plan."""
        ...

    @abstractmethod
    async def save_days(self, athlete_id: str, days: list[PlannedDay]) -> None:
        """Update the days in the cached plan without changing metadata."""
        ...

    @abstractmethod
    async def invalidate(self, athlete_id: str) -> None:
        """Remove the cached plan for an athlete."""
        ...
