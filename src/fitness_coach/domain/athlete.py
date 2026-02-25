"""Athlete domain entity."""

from datetime import date
from enum import Enum
from pydantic import BaseModel, Field

from fitness_coach.domain.workout import WorkoutType


class GoalType(str, Enum):
    """Types of fitness goals."""

    RACE = "race"
    TIME_GOAL = "time_goal"
    DISTANCE_GOAL = "distance_goal"
    GENERAL_FITNESS = "general_fitness"
    WEIGHT_LOSS = "weight_loss"
    STRENGTH = "strength"


class Goal(BaseModel):
    """A fitness goal."""

    goal_type: GoalType
    description: str
    target_date: date | None = None
    target_value: str | None = None  # e.g., "sub 3:30 marathon", "10km in 45min"
    priority: int = Field(default=1, ge=1, le=5)


class Injury(BaseModel):
    """An injury or physical limitation."""

    description: str
    affected_area: str
    start_date: date
    end_date: date | None = None
    restrictions: list[str] = Field(default_factory=list)


class ScheduleTemplateSlot(BaseModel):
    """A recurring planned workout slot — sport on a given day of week."""

    workout_type: WorkoutType
    day_of_week: int = Field(ge=0, le=6)  # 0 = Monday, 6 = Sunday


class Athlete(BaseModel):
    """The athlete profile - persistent user information."""

    id: str
    name: str
    date_of_birth: date | None = None
    weight_kg: float | None = None
    height_cm: float | None = None

    # Experience and background
    experience_years: float = 0
    sports_background: list[str] = Field(default_factory=list)

    # Goals and limitations
    goals: list[Goal] = Field(default_factory=list)
    injuries: list[Injury] = Field(default_factory=list)

    # Preferences
    preferred_workout_days: list[str] = Field(default_factory=list)
    max_hours_per_week: float | None = None
    notes: str = ""
    schedule_template: list[ScheduleTemplateSlot] = Field(default_factory=list)

    # Strava integration
    strava_athlete_id: int | None = None

    @property
    def age(self) -> int | None:
        """Calculate age from date of birth."""
        if not self.date_of_birth:
            return None
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )

    def with_primary_goal(self, goal: "Goal") -> "Athlete":
        return self.model_copy(update={"goals": [goal]})

    def without_primary_goal(self) -> "Athlete":
        return self.model_copy(update={"goals": []})

    def with_schedule_slot(self, slot: "ScheduleTemplateSlot") -> "Athlete":
        return self.model_copy(update={"schedule_template": [*self.schedule_template, slot]})

    def without_schedule_slot(self, slot_index: int) -> "Athlete":
        if slot_index < 0 or slot_index >= len(self.schedule_template):
            raise IndexError(f"Slot index {slot_index} out of range")
        slots = list(self.schedule_template)
        slots.pop(slot_index)
        return self.model_copy(update={"schedule_template": slots})

    @property
    def active_injuries(self) -> list[Injury]:
        """Get currently active injuries."""
        return [i for i in self.injuries if i.end_date is None]

    @property
    def primary_goal(self) -> Goal | None:
        """Get the highest priority goal."""
        if not self.goals:
            return None
        return min(self.goals, key=lambda g: g.priority)
