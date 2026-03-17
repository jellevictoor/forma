"""Domain tests for Athlete aggregate methods."""

import pytest

from forma.domain.athlete import Athlete, Goal, GoalType, ScheduleTemplateSlot
from forma.domain.workout import WorkoutType


@pytest.fixture
def athlete():
    return Athlete(id="a1", name="Test Athlete")


@pytest.fixture
def goal():
    return Goal(goal_type=GoalType.RACE, description="Run a marathon")


@pytest.fixture
def slot():
    return ScheduleTemplateSlot(workout_type=WorkoutType.RUN, day_of_week=1)


def test_with_primary_goal_replaces_all_goals(athlete, goal):
    second_goal = Goal(goal_type=GoalType.GENERAL_FITNESS, description="Stay fit")
    athlete_with_two = athlete.model_copy(update={"goals": [goal, second_goal]})

    result = athlete_with_two.with_primary_goal(goal)

    assert result.goals == [goal]


def test_with_primary_goal_returns_new_instance(athlete, goal):
    result = athlete.with_primary_goal(goal)

    assert result is not athlete


def test_without_primary_goal_clears_goals(athlete, goal):
    athlete_with_goal = athlete.model_copy(update={"goals": [goal]})

    result = athlete_with_goal.without_primary_goal()

    assert result.goals == []


def test_with_schedule_slot_appends_slot(athlete, slot):
    result = athlete.with_schedule_slot(slot)

    assert result.schedule_template == [slot]


def test_without_schedule_slot_removes_by_index(athlete, slot):
    second_slot = ScheduleTemplateSlot(workout_type=WorkoutType.RUN, day_of_week=3)
    athlete_with_slots = athlete.model_copy(update={"schedule_template": [slot, second_slot]})

    result = athlete_with_slots.without_schedule_slot(0)

    assert result.schedule_template == [second_slot]


def test_without_schedule_slot_raises_on_out_of_range_index(athlete, slot):
    athlete_with_slot = athlete.model_copy(update={"schedule_template": [slot]})

    with pytest.raises(IndexError):
        athlete_with_slot.without_schedule_slot(5)
