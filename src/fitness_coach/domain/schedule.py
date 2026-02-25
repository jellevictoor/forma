"""Training schedule domain entity."""

from datetime import date
from enum import Enum
from pydantic import BaseModel, Field

from .workout import WorkoutType


class TrainingPhase(str, Enum):
    """Training periodization phases."""

    BASE = "base"
    BUILD = "build"
    PEAK = "peak"
    TAPER = "taper"
    RECOVERY = "recovery"


class IntensityLevel(str, Enum):
    """Workout intensity levels."""

    RECOVERY = "recovery"
    EASY = "easy"
    MODERATE = "moderate"
    TEMPO = "tempo"
    THRESHOLD = "threshold"
    INTERVAL = "interval"
    RACE = "race"


class ScheduledWorkout(BaseModel):
    """A planned workout in the schedule."""

    id: str
    day_of_week: int = Field(ge=0, le=6)  # 0 = Monday, 6 = Sunday
    week_number: int = Field(ge=1)

    workout_type: WorkoutType
    intensity: IntensityLevel
    description: str

    # Targets
    target_duration_minutes: int | None = None
    target_distance_km: float | None = None
    target_pace_description: str | None = None  # e.g., "easy pace", "5:30/km"

    # Optional structured workout
    structured_workout: str = ""  # e.g., "10min warmup, 5x1000m @ 4:30, 10min cooldown"

    # Flexibility
    is_optional: bool = False
    alternatives: list[str] = Field(default_factory=list)

    notes: str = ""


class WeekSummary(BaseModel):
    """Summary of a training week."""

    week_number: int
    phase: TrainingPhase
    focus: str
    total_hours: float | None = None
    total_distance_km: float | None = None
    notes: str = ""


class Schedule(BaseModel):
    """The training schedule/plan."""

    id: str
    athlete_id: str
    name: str
    description: str = ""

    # Schedule period
    start_date: date
    end_date: date | None = None
    current_week: int = 1

    # Goal this schedule is working towards
    target_event: str | None = None
    target_event_date: date | None = None

    # Structure
    weeks: list[WeekSummary] = Field(default_factory=list)
    workouts: list[ScheduledWorkout] = Field(default_factory=list)

    # Current phase
    current_phase: TrainingPhase = TrainingPhase.BASE

    notes: str = ""

    def get_week_workouts(self, week_number: int) -> list[ScheduledWorkout]:
        """Get all workouts for a specific week."""
        return [w for w in self.workouts if w.week_number == week_number]

    def get_current_week_workouts(self) -> list[ScheduledWorkout]:
        """Get workouts for the current week."""
        return self.get_week_workouts(self.current_week)

    def get_today_workout(self) -> ScheduledWorkout | None:
        """Get today's scheduled workout."""
        today = date.today()
        day_of_week = today.weekday()
        current_workouts = self.get_current_week_workouts()
        for workout in current_workouts:
            if workout.day_of_week == day_of_week:
                return workout
        return None
