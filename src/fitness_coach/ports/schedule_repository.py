"""Port for schedule persistence."""

from abc import ABC, abstractmethod

from fitness_coach.domain.schedule import Schedule


class ScheduleRepository(ABC):
    """Abstract repository for training schedule data."""

    @abstractmethod
    async def get(self, schedule_id: str) -> Schedule | None:
        """Get a schedule by ID."""
        ...

    @abstractmethod
    async def get_active_for_athlete(self, athlete_id: str) -> Schedule | None:
        """Get the currently active schedule for an athlete."""
        ...

    @abstractmethod
    async def save(self, schedule: Schedule) -> None:
        """Save a schedule."""
        ...

    @abstractmethod
    async def delete(self, schedule_id: str) -> None:
        """Delete a schedule."""
        ...

    @abstractmethod
    async def list_schedules_for_athlete(self, athlete_id: str) -> list[Schedule]:
        """List all schedules for an athlete."""
        ...
