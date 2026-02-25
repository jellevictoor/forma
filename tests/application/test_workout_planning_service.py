"""Tests for WorkoutPlanningService."""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch


from fitness_coach.application.workout_planning_service import WorkoutPlanningService
from fitness_coach.domain.athlete import Athlete
from fitness_coach.domain.workout import Workout, WorkoutType
from fitness_coach.ports.plan_cache_repository import CachedWeeklyPlan, PlannedDay, WeeklyPlan


def make_athlete() -> Athlete:
    return Athlete(id="athlete1", name="Jane Doe")


def make_workout(workout_id: str, workout_type: WorkoutType, days_ago: int) -> Workout:
    start = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    return Workout(
        id=workout_id,
        athlete_id="athlete1",
        workout_type=workout_type,
        name="Test",
        start_time=start,
        duration_seconds=3600,
    )


def make_plan() -> WeeklyPlan:
    return WeeklyPlan(
        days=[
            PlannedDay(
                day=date.today(),
                workout_type="run",
                intensity="easy",
                duration_minutes=45,
                description="Easy run.",
            )
        ],
        rationale="Focus on recovery.",
        generated_at=datetime.now(tz=timezone.utc),
    )


def make_deps():
    athlete_repo = AsyncMock()
    athlete_repo.get = AsyncMock(return_value=make_athlete())
    workout_repo = AsyncMock()
    workout_repo.get_recent = AsyncMock(return_value=[])
    workout_repo.list_workouts_for_athlete = AsyncMock(return_value=[])
    analytics_repo = AsyncMock()
    analytics_repo.daily_effort = AsyncMock(return_value=[])
    plan_cache = AsyncMock()
    plan_cache.get = AsyncMock(return_value=None)
    plan_cache.save = AsyncMock()
    plan_cache.invalidate = AsyncMock()
    return athlete_repo, workout_repo, analytics_repo, plan_cache


def make_service(athlete_repo=None, workout_repo=None, analytics_repo=None, plan_cache=None):
    deps = make_deps()
    return WorkoutPlanningService(
        athlete_repo=athlete_repo or deps[0],
        workout_repo=workout_repo or deps[1],
        analytics_repo=analytics_repo or deps[2],
        gemini_api_key="fake-key",
        plan_cache_repo=plan_cache or deps[3],
    )


async def test_get_cached_returns_none_when_no_cache():
    service = make_service()

    result = await service.get_cached("athlete1")

    assert result is None


async def test_get_cached_sets_stale_false_when_no_new_activity():
    cached_at = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    activity_time = cached_at - timedelta(hours=1)
    cached = CachedWeeklyPlan(
        days=[],
        rationale="Good week.",
        generated_at=cached_at,
        latest_activity_at=activity_time,
    )
    _, workout_repo, analytics_repo, plan_cache = make_deps()
    plan_cache.get = AsyncMock(return_value=cached)
    workout_repo.get_recent = AsyncMock(return_value=[make_workout("w1", WorkoutType.RUN, days_ago=2)])
    service = make_service(workout_repo=workout_repo, analytics_repo=analytics_repo, plan_cache=plan_cache)

    result = await service.get_cached("athlete1")

    assert result.is_stale is False


async def test_get_cached_sets_stale_true_when_new_activity_exists():
    cached_at = datetime.now(tz=timezone.utc) - timedelta(hours=2)
    activity_time = cached_at - timedelta(hours=1)
    cached = CachedWeeklyPlan(
        days=[],
        rationale="Good week.",
        generated_at=cached_at,
        latest_activity_at=activity_time,
    )
    new_workout = make_workout("w1", WorkoutType.RUN, days_ago=0)
    _, workout_repo, analytics_repo, plan_cache = make_deps()
    plan_cache.get = AsyncMock(return_value=cached)
    workout_repo.get_recent = AsyncMock(return_value=[new_workout])
    service = make_service(workout_repo=workout_repo, analytics_repo=analytics_repo, plan_cache=plan_cache)

    result = await service.get_cached("athlete1")

    assert result.is_stale is True


async def test_generate_and_cache_returns_cached_weekly_plan():
    service = make_service()

    with patch.object(service, "_call_gemini_for_plan", return_value=make_plan()):
        result = await service.generate_and_cache("athlete1")

    assert isinstance(result, CachedWeeklyPlan)


async def test_generate_and_cache_saves_to_cache():
    _, workout_repo, analytics_repo, plan_cache = make_deps()
    service = make_service(workout_repo=workout_repo, analytics_repo=analytics_repo, plan_cache=plan_cache)

    with patch.object(service, "_call_gemini_for_plan", return_value=make_plan()):
        await service.generate_and_cache("athlete1")

    plan_cache.save.assert_called_once()


async def test_generate_and_cache_calls_gemini():
    service = make_service()

    with patch.object(service, "_call_gemini_for_plan", return_value=make_plan()) as mock_gemini:
        await service.generate_and_cache("athlete1")

    mock_gemini.assert_called_once()


async def test_generate_and_cache_returns_plan_with_days():
    service = make_service()

    with patch.object(service, "_call_gemini_for_plan", return_value=make_plan()):
        result = await service.generate_and_cache("athlete1")

    assert len(result.days) == 1


async def test_get_exercises_returns_dict():
    service = make_service()
    sections = {"warmup": ["5 min jog"], "main": ["3x10 squats"], "cooldown": ["stretch"]}

    with patch.object(service, "_call_gemini_for_exercises", return_value=sections):
        result = await service.get_exercises_for_day("athlete1", date.today(), "strength")

    assert isinstance(result, dict)


async def test_get_exercises_calls_gemini_when_not_cached():
    service = make_service()

    with patch.object(service, "_call_gemini_for_exercises", return_value=[]) as mock_gemini:
        await service.get_exercises_for_day("athlete1", date.today(), "strength")

    mock_gemini.assert_called_once()


async def test_get_exercises_returns_cached_exercises_without_calling_gemini():
    _, _, _, plan_cache = make_deps()
    cached_exercises = {"warmup": ["5 min jog"], "main": ["3x10 squats"], "cooldown": ["stretch"]}
    cached_day = PlannedDay(
        day=date.today(), workout_type="run", intensity="easy",
        duration_minutes=45, description="Easy run.", exercises=cached_exercises
    )
    plan_cache.get = AsyncMock(return_value=CachedWeeklyPlan(
        days=[cached_day], rationale="", generated_at=datetime.now(tz=timezone.utc)
    ))
    service = make_service(plan_cache=plan_cache)

    with patch.object(service, "_call_gemini_for_exercises") as mock_gemini:
        result = await service.get_exercises_for_day("athlete1", date.today(), "run")

    assert result == cached_exercises
    mock_gemini.assert_not_called()


async def test_refresh_exercises_always_calls_gemini_even_when_cached():
    _, _, _, plan_cache = make_deps()
    cached_day = PlannedDay(
        day=date.today(), workout_type="run", intensity="easy",
        duration_minutes=45, description="Easy run.",
        exercises={"warmup": [], "main": ["Old exercise"], "cooldown": []}
    )
    plan_cache.get = AsyncMock(return_value=CachedWeeklyPlan(
        days=[cached_day], rationale="", generated_at=datetime.now(tz=timezone.utc)
    ))
    plan_cache.update_day_exercises = AsyncMock()
    service = make_service(plan_cache=plan_cache)

    new_exercises = {"warmup": [], "main": ["New exercise"], "cooldown": []}
    with patch.object(service, "_call_gemini_for_exercises", return_value=new_exercises) as mock_gemini:
        result = await service.refresh_exercises_for_day("athlete1", date.today(), "run")

    assert result == new_exercises
    mock_gemini.assert_called_once()


async def test_get_exercises_caches_result_after_generating():
    _, _, _, plan_cache = make_deps()
    plan_cache.update_day_exercises = AsyncMock()
    service = make_service(plan_cache=plan_cache)

    with patch.object(service, "_call_gemini_for_exercises", return_value=["Warm-up: 5 min"]):
        await service.get_exercises_for_day("athlete1", date.today(), "strength")

    plan_cache.update_day_exercises.assert_called_once()


async def test_plan_excludes_days_with_completed_workouts():
    _, workout_repo, analytics_repo, plan_cache = make_deps()
    today_workout = make_workout("w1", WorkoutType.RUN, days_ago=0)
    workout_repo.list_workouts_for_athlete = AsyncMock(return_value=[today_workout])
    service = make_service(workout_repo=workout_repo, analytics_repo=analytics_repo, plan_cache=plan_cache)

    captured_prompt = []

    def capture_plan(prompt):
        captured_prompt.append(prompt)
        return WeeklyPlan(days=[PlannedDay(day=date.today() + timedelta(days=1), workout_type="rest", intensity="recovery", duration_minutes=0, description="Rest.")], rationale="", generated_at=datetime.now(tz=timezone.utc))

    with patch.object(service, "_call_gemini_for_plan", side_effect=capture_plan):
        await service.generate_and_cache("athlete1")

    assert date.today().isoformat() not in captured_prompt[0]


async def test_plan_includes_days_without_completed_workouts():
    _, workout_repo, analytics_repo, plan_cache = make_deps()
    today_workout = make_workout("w1", WorkoutType.RUN, days_ago=0)
    workout_repo.list_workouts_for_athlete = AsyncMock(return_value=[today_workout])
    service = make_service(workout_repo=workout_repo, analytics_repo=analytics_repo, plan_cache=plan_cache)

    captured_prompt = []

    def capture_plan(prompt):
        captured_prompt.append(prompt)
        return WeeklyPlan(days=[PlannedDay(day=date.today() + timedelta(days=1), workout_type="rest", intensity="recovery", duration_minutes=0, description="Rest.")], rationale="", generated_at=datetime.now(tz=timezone.utc))

    with patch.object(service, "_call_gemini_for_plan", side_effect=capture_plan):
        await service.generate_and_cache("athlete1")

    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert tomorrow in captured_prompt[0]
