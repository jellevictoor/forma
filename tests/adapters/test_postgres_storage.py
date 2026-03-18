"""Integration tests for PostgresStorage (athletes, workouts, weight entries)."""

from datetime import date, datetime, timezone

import pytest

from forma.adapters.postgres_storage import PostgresStorage
from forma.domain.athlete import Athlete, Role
from forma.domain.weight_entry import WeightEntry
from forma.domain.workout import Workout, WorkoutType


@pytest.fixture
def storage(pool):
    return PostgresStorage(pool)


@pytest.fixture
async def saved_athlete(storage):
    athlete = Athlete(id="athlete-1", name="Test Runner")
    await storage.save(athlete)
    return athlete


def _workout(athlete_id: str, workout_id: str = "workout-1") -> Workout:
    return Workout(
        id=workout_id,
        athlete_id=athlete_id,
        workout_type=WorkoutType.RUN,
        name="Morning Run",
        start_time=datetime(2025, 1, 15, 8, 0, tzinfo=timezone.utc),
        duration_seconds=3600,
    )


# --- Athlete ---


async def test_get_athlete_returns_none_when_not_found(storage):
    result = await storage.get("nonexistent")

    assert result is None


async def test_save_and_get_athlete_by_id(storage, saved_athlete):
    result = await storage.get(saved_athlete.id)

    assert result.name == "Test Runner"


async def test_save_athlete_preserves_role(storage):
    athlete = Athlete(id="athlete-2", name="Admin", role=Role.SUPERADMIN)
    await storage.save(athlete)

    result = await storage.get("athlete-2")

    assert result.role == Role.SUPERADMIN


async def test_save_athlete_upserts_on_conflict(storage, saved_athlete):
    updated = Athlete(id=saved_athlete.id, name="Updated Name")
    await storage.save(updated)

    result = await storage.get(saved_athlete.id)

    assert result.name == "Updated Name"


async def test_get_by_strava_id_returns_athlete(storage):
    athlete = Athlete(id="athlete-3", name="Strava User", strava_athlete_id=12345)
    await storage.save(athlete)

    result = await storage.get_by_strava_id(12345)

    assert result.id == "athlete-3"


async def test_get_by_strava_id_returns_none_when_not_found(storage):
    result = await storage.get_by_strava_id(99999)

    assert result is None


async def test_delete_athlete_removes_record(storage, saved_athlete):
    await storage.delete(saved_athlete.id)

    result = await storage.get(saved_athlete.id)

    assert result is None


# --- Workout ---


async def test_get_workout_returns_none_when_not_found(storage):
    result = await storage.get_workout("nonexistent")

    assert result is None


async def test_save_and_get_workout(storage, saved_athlete):
    workout = _workout(saved_athlete.id)
    await storage.save_workout(workout)

    result = await storage.get_workout(workout.id)

    assert result.name == "Morning Run"


async def test_save_workout_upserts_on_conflict(storage, saved_athlete):
    workout = _workout(saved_athlete.id)
    await storage.save_workout(workout)
    updated = workout.model_copy(update={"name": "Evening Run"})
    await storage.save_workout(updated)

    result = await storage.get_workout(workout.id)

    assert result.name == "Evening Run"


async def test_list_workouts_for_athlete_returns_all(storage, saved_athlete):
    for i in range(3):
        await storage.save_workout(_workout(saved_athlete.id, f"w-{i}"))

    result = await storage.list_workouts_for_athlete(saved_athlete.id)

    assert len(result) == 3


async def test_delete_workout_removes_record(storage, saved_athlete):
    workout = _workout(saved_athlete.id)
    await storage.save_workout(workout)
    await storage.delete_workout(workout.id)

    result = await storage.get_workout(workout.id)

    assert result is None


# --- Weight ---


async def test_save_and_list_weight_entries(storage, saved_athlete):
    entry = WeightEntry(
        id="weight-1",
        athlete_id=saved_athlete.id,
        weight_kg=75.5,
        recorded_at=date(2025, 1, 15),
    )
    await storage.save_weight_entry(entry)

    result = await storage.list_weight_entries(saved_athlete.id)

    assert result[0].weight_kg == 75.5


async def test_get_latest_weight_returns_most_recent(storage, saved_athlete):
    for i, kg in enumerate([70.0, 72.5, 71.0]):
        await storage.save_weight_entry(WeightEntry(
            id=f"weight-{i}",
            athlete_id=saved_athlete.id,
            weight_kg=kg,
            recorded_at=date(2025, 1, i + 1),
        ))

    result = await storage.get_latest_weight(saved_athlete.id)

    assert result.weight_kg == 71.0
