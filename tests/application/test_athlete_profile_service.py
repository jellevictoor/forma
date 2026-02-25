"""Tests for AthleteProfileService."""

from unittest.mock import AsyncMock

import pytest

from fitness_coach.application.athlete_profile_service import AthleteProfileService
from fitness_coach.domain.athlete import Athlete, Goal, GoalType, ScheduleTemplateSlot
from fitness_coach.domain.workout import WorkoutType


def make_athlete(athlete_id: str = "athlete1") -> Athlete:
    return Athlete(id=athlete_id, name="Jane Doe")


def make_service(athlete: Athlete | None = None) -> AthleteProfileService:
    athlete_repo = AsyncMock()
    athlete_repo.get = AsyncMock(return_value=athlete or make_athlete())
    athlete_repo.save = AsyncMock()
    workout_repo = AsyncMock()
    workout_repo.get_recent = AsyncMock(return_value=[])
    return AthleteProfileService(athlete_repo, workout_repo, gemini_api_key="fake-key")


@pytest.mark.asyncio
async def test_update_profile_name():
    service = make_service()

    updated = await service.update_profile("athlete1", {"name": "John Doe"})

    assert updated.name == "John Doe"


@pytest.mark.asyncio
async def test_set_primary_goal_replaces_existing():
    athlete = make_athlete()
    athlete = athlete.model_copy(
        update={"goals": [Goal(goal_type=GoalType.GENERAL_FITNESS, description="Stay fit")]}
    )
    service = make_service(athlete)
    new_goal = Goal(goal_type=GoalType.RACE, description="Run a marathon")

    result = await service.set_primary_goal("athlete1", new_goal)

    assert len(result.goals) == 1
    assert result.goals[0].description == "Run a marathon"


@pytest.mark.asyncio
async def test_remove_primary_goal_clears_goals():
    athlete = make_athlete()
    athlete = athlete.model_copy(
        update={"goals": [Goal(goal_type=GoalType.RACE, description="Run a marathon")]}
    )
    service = make_service(athlete)

    result = await service.remove_primary_goal("athlete1")

    assert result.goals == []


@pytest.mark.asyncio
async def test_add_schedule_slot_appends_slot():
    service = make_service()
    slot = ScheduleTemplateSlot(workout_type=WorkoutType.RUN, day_of_week=0)

    result = await service.add_schedule_slot("athlete1", slot)

    assert len(result.schedule_template) == 1


@pytest.mark.asyncio
async def test_add_schedule_slot_persists_correct_type():
    service = make_service()
    slot = ScheduleTemplateSlot(workout_type=WorkoutType.CLIMBING, day_of_week=3)

    result = await service.add_schedule_slot("athlete1", slot)

    assert result.schedule_template[0].workout_type == WorkoutType.CLIMBING


@pytest.mark.asyncio
async def test_add_schedule_slot_persists_correct_day():
    service = make_service()
    slot = ScheduleTemplateSlot(workout_type=WorkoutType.RUN, day_of_week=4)

    result = await service.add_schedule_slot("athlete1", slot)

    assert result.schedule_template[0].day_of_week == 4


@pytest.mark.asyncio
async def test_add_schedule_slot_saves_athlete():
    athlete_repo = AsyncMock()
    athlete_repo.get = AsyncMock(return_value=make_athlete())
    athlete_repo.save = AsyncMock()
    workout_repo = AsyncMock()
    service = AthleteProfileService(athlete_repo, workout_repo, gemini_api_key="fake-key")
    slot = ScheduleTemplateSlot(workout_type=WorkoutType.STRENGTH, day_of_week=1)

    await service.add_schedule_slot("athlete1", slot)

    athlete_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_remove_schedule_slot_removes_correct_slot():
    athlete = make_athlete()
    athlete = athlete.model_copy(update={"schedule_template": [
        ScheduleTemplateSlot(workout_type=WorkoutType.RUN, day_of_week=0),
        ScheduleTemplateSlot(workout_type=WorkoutType.CLIMBING, day_of_week=3),
    ]})
    service = make_service(athlete)

    result = await service.remove_schedule_slot("athlete1", 0)

    assert len(result.schedule_template) == 1
    assert result.schedule_template[0].workout_type == WorkoutType.CLIMBING


@pytest.mark.asyncio
async def test_remove_schedule_slot_saves_athlete():
    athlete = make_athlete()
    athlete = athlete.model_copy(update={"schedule_template": [
        ScheduleTemplateSlot(workout_type=WorkoutType.RUN, day_of_week=0),
    ]})
    athlete_repo = AsyncMock()
    athlete_repo.get = AsyncMock(return_value=athlete)
    athlete_repo.save = AsyncMock()
    workout_repo = AsyncMock()
    service = AthleteProfileService(athlete_repo, workout_repo, gemini_api_key="fake-key")

    await service.remove_schedule_slot("athlete1", 0)

    athlete_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_remove_schedule_slot_raises_on_invalid_index():
    service = make_service()

    with pytest.raises(IndexError):
        await service.remove_schedule_slot("athlete1", 5)
