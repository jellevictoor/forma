"""Port for the AI coach interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from fitness_coach.domain.athlete import Athlete
from fitness_coach.domain.schedule import Schedule
from fitness_coach.domain.workout import Workout


@dataclass
class CoachContext:
    """Context provided to the coach for a conversation."""

    athlete: Athlete
    schedule: Schedule | None = None
    recent_workouts: list[Workout] | None = None
    conversation_history: list[dict] | None = None


@dataclass
class CoachResponse:
    """Response from the coach."""

    message: str
    suggested_actions: list[str] | None = None


class Coach(ABC):
    """Abstract AI coach interface."""

    @abstractmethod
    async def chat(self, message: str, context: CoachContext) -> CoachResponse:
        """Send a message to the coach and get a response."""
        ...

    @abstractmethod
    async def analyze_workout(self, workout: Workout, context: CoachContext) -> CoachResponse:
        """Get the coach's analysis of a completed workout."""
        ...

    @abstractmethod
    async def get_daily_briefing(self, context: CoachContext) -> CoachResponse:
        """Get a daily briefing from the coach."""
        ...

    @abstractmethod
    async def suggest_schedule_adjustment(
        self,
        reason: str,
        context: CoachContext,
    ) -> CoachResponse:
        """Ask the coach to suggest schedule adjustments."""
        ...
