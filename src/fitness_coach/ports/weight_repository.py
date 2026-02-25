"""Port for weight entry persistence."""

from abc import ABC, abstractmethod

from fitness_coach.domain.weight_entry import WeightEntry


class WeightRepository(ABC):
    """Abstract repository for weight tracking entries."""

    @abstractmethod
    async def save_weight_entry(self, entry: WeightEntry) -> None:
        """Save a weight entry."""
        ...

    @abstractmethod
    async def list_weight_entries(self, athlete_id: str, limit: int = 90) -> list[WeightEntry]:
        """List weight entries for an athlete, newest first."""
        ...

    @abstractmethod
    async def get_latest_weight(self, athlete_id: str) -> WeightEntry | None:
        """Get the most recent weight entry for an athlete."""
        ...

    @abstractmethod
    async def delete_weight_entry(self, entry_id: str) -> None:
        """Delete a weight entry by ID."""
        ...
