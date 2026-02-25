"""Port for athlete persistence."""

from abc import ABC, abstractmethod

from fitness_coach.domain.athlete import Athlete


class AthleteRepository(ABC):
    """Abstract repository for athlete data."""

    @abstractmethod
    async def get(self, athlete_id: str) -> Athlete | None:
        """Get an athlete by ID."""
        ...

    @abstractmethod
    async def save(self, athlete: Athlete) -> None:
        """Save an athlete."""
        ...

    @abstractmethod
    async def delete(self, athlete_id: str) -> None:
        """Delete an athlete."""
        ...

    @abstractmethod
    async def get_default(self) -> Athlete | None:
        """Get the default/primary athlete (for single-user mode)."""
        ...

    @abstractmethod
    async def set_default(self, athlete_id: str) -> None:
        """Mark an athlete as the default (for single-user mode)."""
        ...
