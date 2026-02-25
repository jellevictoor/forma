"""Port for workout persistence."""

from abc import ABC, abstractmethod
from datetime import date

from fitness_coach.domain.workout import Workout


class WorkoutRepository(ABC):
    """Abstract repository for workout data."""

    @abstractmethod
    async def get_workout(self, workout_id: str) -> Workout | None:
        """Get a workout by ID."""
        ...

    @abstractmethod
    async def get_workout_by_strava_id(self, strava_id: int) -> Workout | None:
        """Get a workout by its Strava ID."""
        ...

    @abstractmethod
    async def save_workout(self, workout: Workout) -> None:
        """Save a workout."""
        ...

    @abstractmethod
    async def delete_workout(self, workout_id: str) -> None:
        """Delete a workout."""
        ...

    @abstractmethod
    async def list_workouts_for_athlete(
        self,
        athlete_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> list[Workout]:
        """List workouts for an athlete, optionally filtered by date range."""
        ...

    @abstractmethod
    async def get_recent(self, athlete_id: str, count: int = 10) -> list[Workout]:
        """Get the most recent workouts for an athlete."""
        ...
