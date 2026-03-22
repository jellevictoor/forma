"""Long run detection — identifies runs that qualify as 'long runs' for endurance training."""

from forma.domain.workout import Workout, WorkoutType

# A run is "long" if it's >= 60 min OR >= 10 km
LONG_RUN_MIN_DURATION = 60 * 60  # 60 minutes in seconds
LONG_RUN_MIN_DISTANCE = 10000    # 10 km in meters


def is_long_run(workout: Workout) -> bool:
    """Check if a workout qualifies as a long run."""
    if workout.workout_type != WorkoutType.RUN:
        return False
    if workout.duration_seconds >= LONG_RUN_MIN_DURATION:
        return True
    if workout.distance_meters and workout.distance_meters >= LONG_RUN_MIN_DISTANCE:
        return True
    return False


def long_run_summary(workouts: list[Workout]) -> dict:
    """Compute long run stats from a list of workouts."""
    long_runs = [w for w in workouts if is_long_run(w)]
    if not long_runs:
        return {"count": 0, "longest_km": None, "avg_km": None, "total_km": 0}

    distances = [w.distance_km or 0 for w in long_runs]
    return {
        "count": len(long_runs),
        "longest_km": round(max(distances), 1),
        "avg_km": round(sum(distances) / len(distances), 1),
        "total_km": round(sum(distances), 1),
    }
