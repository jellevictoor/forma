"""Workout domain entity."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel


class WorkoutType(str, Enum):
    """Types of workouts."""

    RUN = "run"
    BIKE = "bike"
    SWIM = "swim"
    STRENGTH = "strength"
    YOGA = "yoga"
    WALK = "walk"
    HIKE = "hike"
    CLIMBING = "climbing"
    CROSS_TRAINING = "cross_training"
    REST = "rest"
    OTHER = "other"


class PerceivedEffort(str, Enum):
    """How hard the workout felt."""

    VERY_EASY = "very_easy"
    EASY = "easy"
    MODERATE = "moderate"
    HARD = "hard"
    VERY_HARD = "very_hard"
    MAXIMUM = "maximum"


class Workout(BaseModel):
    """A completed workout, typically synced from Strava."""

    id: str
    strava_id: int | None = None
    athlete_id: str

    workout_type: WorkoutType
    name: str
    description: str = ""

    # Timing
    start_time: datetime
    duration_seconds: int
    moving_time_seconds: int | None = None

    # Distance and pace
    distance_meters: float | None = None
    average_speed_mps: float | None = None
    max_speed_mps: float | None = None

    # Heart rate
    average_heartrate: float | None = None
    max_heartrate: float | None = None

    # Elevation
    elevation_gain_meters: float | None = None

    # Subjective feedback (from Strava private notes)
    private_note: str = ""
    perceived_effort: PerceivedEffort | None = None
    mood: str = ""
    sleep_quality: str = ""

    # Calculated fields
    @property
    def duration_minutes(self) -> float:
        """Duration in minutes."""
        return self.duration_seconds / 60

    @property
    def distance_km(self) -> float | None:
        """Distance in kilometers."""
        if self.distance_meters is None:
            return None
        return self.distance_meters / 1000

    @property
    def pace_min_per_km(self) -> float | None:
        """Pace in minutes per kilometer."""
        if not self.distance_meters or not self.moving_time_seconds:
            return None
        km = self.distance_meters / 1000
        if km == 0:
            return None
        return (self.moving_time_seconds / 60) / km

    def pace_formatted(self) -> str | None:
        """Pace as MM:SS per km."""
        pace = self.pace_min_per_km
        if pace is None:
            return None
        minutes = int(pace)
        seconds = int((pace - minutes) * 60)
        return f"{minutes}:{seconds:02d}/km"
