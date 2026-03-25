"""Match synced activities to planned workouts."""

from dataclasses import dataclass

from forma.domain.workout import Workout
from forma.ports.plan_cache_repository import PlannedDay

# Strava workout types that map to plan types
TYPE_COMPATIBILITY = {
    "run": {"run", "trail_run", "virtual_run"},
    "strength": {"strength", "cross_training", "weight_training"},
    "climbing": {"climbing", "rock_climbing", "bouldering"},
    "walk": {"walk", "hike"},
    "cross_training": {"cross_training", "elliptical", "stair_stepper"},
    "bike": {"bike", "ebike", "virtual_ride", "ride"},
    "swim": {"swim"},
    "yoga": {"yoga"},
}


@dataclass
class PlanMatch:
    description: str
    exercises: dict[str, list[str]] | None


def types_compatible(plan_type: str, workout_type: str) -> bool:
    """Check if a workout type is compatible with a planned type."""
    if plan_type == workout_type:
        return True
    compatible = TYPE_COMPATIBILITY.get(plan_type, set())
    return workout_type in compatible


def match_workout_to_plan(workout: Workout, plan_days: list[PlannedDay]) -> PlanMatch | None:
    """Find the matching plan day for a workout.

    Returns PlanMatch with description + exercises, or None if no match.
    """
    workout_date = workout.start_time.date()
    workout_type = workout.workout_type.value

    for day in plan_days:
        if day.day != workout_date:
            continue
        if day.workout_type == "rest":
            continue
        if types_compatible(day.workout_type, workout_type):
            exercises = day.exercises if day.exercises else None
            return PlanMatch(description=day.description, exercises=exercises)

    return None
