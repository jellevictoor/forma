"""Workout execution session domain model."""

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class ExecutionExercise:
    """A single exercise during a workout session."""

    id: str  # e.g., "warmup-0", "main-2"
    phase: str  # "warmup" | "main" | "cooldown"
    text: str  # original exercise text
    completed: bool = False


@dataclass
class ExecutionSession:
    """An active or completed workout execution session."""

    session_id: str
    athlete_id: str
    date: date
    workout_type: str
    exercises: list[ExecutionExercise]
    started_at: datetime
    completed_at: datetime | None = None

    def complete_exercise(self, exercise_id: str) -> None:
        """Mark an exercise as completed."""
        for ex in self.exercises:
            if ex.id == exercise_id:
                ex.completed = True
                return
        raise ValueError(f"Exercise {exercise_id} not found in session {self.session_id}")

    def complete(self, completed_at: datetime) -> None:
        """Mark the entire session as completed."""
        self.completed_at = completed_at
