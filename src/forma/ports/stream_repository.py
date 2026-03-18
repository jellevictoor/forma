"""Port for activity GPS and metric streams."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class WorkoutStreams:
    latlng: list[list[float]]
    time: list[int]
    velocity_smooth: list[float]
    heartrate: list[float] | None


class StreamRepository(ABC):
    @abstractmethod
    async def get(self, workout_id: str) -> WorkoutStreams | None:
        """Return cached streams for a workout, or None if not stored."""
        ...

    @abstractmethod
    async def save(self, workout_id: str, streams: WorkoutStreams) -> None:
        """Persist streams for a workout."""
        ...
