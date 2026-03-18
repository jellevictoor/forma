"""Athlete domain entity."""

from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, Field

from forma.domain.workout import WorkoutType


class Role(str, Enum):
    """User role — controls access to admin features."""

    USER = "user"
    SUPERADMIN = "superadmin"


class GoalType(str, Enum):
    """Types of fitness goals."""

    RACE = "race"
    TIME_GOAL = "time_goal"
    DISTANCE_GOAL = "distance_goal"
    GENERAL_FITNESS = "general_fitness"
    WEIGHT_LOSS = "weight_loss"
    STRENGTH = "strength"


class GoalMilestone(BaseModel):
    """A measurable checkpoint on the way to a goal."""

    date: date
    description: str
    target: str | None = None  # e.g. "25km/week", "sub-55min 10k"


class Goal(BaseModel):
    """A fitness goal."""

    goal_type: GoalType
    description: str
    target_date: date | None = None
    target_value: str | None = None  # e.g., "sub 3:30 marathon", "10km in 45min"
    priority: int = Field(default=1, ge=1, le=5)
    set_at: datetime = Field(default_factory=datetime.now)
    milestones: list[GoalMilestone] = Field(default_factory=list)
    coach_rationale: str | None = None


class GoalHistoryEntry(BaseModel):
    """A retired goal — kept so the coach can track intent over time."""

    goal_type: GoalType
    description: str
    target_value: str | None = None
    set_at: datetime
    retired_at: datetime


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

    # Goals and limitations
    goals: list[Goal] = Field(default_factory=list)
    injuries: list[Injury] = Field(default_factory=list)

    # Preferences
    preferred_workout_days: list[str] = Field(default_factory=list)
    max_hours_per_week: float | None = None
    notes: str = ""
    schedule_template: list[ScheduleTemplateSlot] = Field(default_factory=list)
    equipment: list[str] = Field(default_factory=list)

    # Goal history — previous goals kept for coaching context
    goal_history: list[GoalHistoryEntry] = Field(default_factory=list)

    # Physiology
    max_heartrate: int | None = None          # beats per minute; used for HR zone calculation
    aerobic_threshold_bpm: int | None = None  # VT1 / talk-test Z2 ceiling — calibrates zones

    # Access control
    is_blocked: bool = False
    role: Role = Role.USER
    ai_enabled: bool = True
    token_limit_30d: int | None = None  # None = unlimited

    # Strava integration
    strava_athlete_id: int | None = None
    strava_access_token: str | None = None
    strava_refresh_token: str | None = None
    strava_token_expires_at: datetime | None = None

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
        history = self._archive_current_goal()
        return self.model_copy(update={"goals": [goal], "goal_history": history})

    def without_primary_goal(self) -> "Athlete":
        history = self._archive_current_goal()
        return self.model_copy(update={"goals": [], "goal_history": history})

    def _archive_current_goal(self) -> "list[GoalHistoryEntry]":
        history = list(self.goal_history)
        if self.primary_goal:
            history.append(GoalHistoryEntry(
                goal_type=self.primary_goal.goal_type,
                description=self.primary_goal.description,
                target_value=self.primary_goal.target_value,
                set_at=self.primary_goal.set_at,
                retired_at=datetime.now(),
            ))
        return history

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
