"""Tests for WorkoutExecutionService."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

from forma.application.workout_execution_service import WorkoutExecutionService
from forma.domain.execution_session import ExecutionExercise, ExecutionSession


def make_service(
    repo_return_value: ExecutionSession | None = None,
    exercises_return_value: dict | None = None,
) -> WorkoutExecutionService:
    """Create a service with mocked dependencies."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.get = AsyncMock(return_value=repo_return_value)
    repo.get_active_for_athlete = AsyncMock(return_value=repo_return_value)

    planning_service = AsyncMock()
    if exercises_return_value is None:
        exercises_return_value = {
            "warmup": ["5 min jog"],
            "main": ["3x10 squats"],
            "cooldown": ["stretch"],
        }
    planning_service.get_exercises_for_day = AsyncMock(return_value=exercises_return_value)

    return WorkoutExecutionService(repo, planning_service)


async def test_start_session_creates_session_with_exercises():
    """Test that start_session fetches exercises and creates a session."""
    service = make_service()

    session = await service.start_session("athlete1", date(2026, 3, 16), "run")

    assert session.session_id is not None
    assert session.athlete_id == "athlete1"
    assert session.date == date(2026, 3, 16)
    assert session.workout_type == "run"
    assert len(session.exercises) == 3


async def test_start_session_exercises_have_stable_ids():
    """Test that exercise IDs are stable (phase-index format)."""
    service = make_service()

    session = await service.start_session("athlete1", date(2026, 3, 16), "run")

    ex_ids = [ex.id for ex in session.exercises]
    assert "warmup-0" in ex_ids
    assert "main-0" in ex_ids
    assert "cooldown-0" in ex_ids


async def test_start_session_saves_to_repo():
    """Test that start_session saves the session to the repository."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.get = AsyncMock()
    repo.get_active_for_athlete = AsyncMock()

    planning_service = AsyncMock()
    planning_service.get_exercises_for_day = AsyncMock(
        return_value={"warmup": ["jog"], "main": ["squats"]}
    )

    service = WorkoutExecutionService(repo, planning_service)

    await service.start_session("athlete1", date(2026, 3, 16), "run")

    assert repo.save.called


async def test_get_session_returns_session():
    """Test that get_session returns a session from the repo."""
    session = ExecutionSession(
        session_id="session1",
        athlete_id="athlete1",
        date=date(2026, 3, 16),
        workout_type="run",
        exercises=[ExecutionExercise(id="ex1", phase="main", text="jog")],
        started_at=datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc),
    )
    service = make_service(repo_return_value=session)

    result = await service.get_session("session1")

    assert result is not None
    assert result.session_id == "session1"


async def test_get_active_session_returns_incomplete_session():
    """Test that get_active_session returns an incomplete session."""
    session = ExecutionSession(
        session_id="session1",
        athlete_id="athlete1",
        date=date(2026, 3, 16),
        workout_type="run",
        exercises=[],
        started_at=datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc),
    )
    service = make_service(repo_return_value=session)

    result = await service.get_active_session("athlete1")

    assert result is not None
    assert result.session_id == "session1"


async def test_complete_exercise_marks_exercise_done():
    """Test that complete_exercise marks the exercise as completed."""
    session = ExecutionSession(
        session_id="session1",
        athlete_id="athlete1",
        date=date(2026, 3, 16),
        workout_type="run",
        exercises=[
            ExecutionExercise(id="warmup-0", phase="warmup", text="jog"),
            ExecutionExercise(id="main-0", phase="main", text="squats"),
        ],
        started_at=datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc),
    )
    service = make_service(repo_return_value=session)

    updated = await service.complete_exercise("session1", "warmup-0")

    assert updated.exercises[0].completed is True
    assert updated.exercises[1].completed is False


async def test_complete_exercise_saves_to_repo():
    """Test that complete_exercise saves the session."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    session = ExecutionSession(
        session_id="session1",
        athlete_id="athlete1",
        date=date(2026, 3, 16),
        workout_type="run",
        exercises=[ExecutionExercise(id="ex1", phase="main", text="jog")],
        started_at=datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc),
    )
    repo.get = AsyncMock(return_value=session)

    planning_service = AsyncMock()
    service = WorkoutExecutionService(repo, planning_service)

    await service.complete_exercise("session1", "ex1")

    assert repo.save.called


async def test_finish_session_sets_completed_at():
    """Test that finish_session sets the completed_at timestamp."""
    session = ExecutionSession(
        session_id="session1",
        athlete_id="athlete1",
        date=date(2026, 3, 16),
        workout_type="run",
        exercises=[],
        started_at=datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc),
    )
    service = make_service(repo_return_value=session)

    updated = await service.finish_session("session1")

    assert updated.completed_at is not None


async def test_finish_session_saves_to_repo():
    """Test that finish_session saves the session."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    session = ExecutionSession(
        session_id="session1",
        athlete_id="athlete1",
        date=date(2026, 3, 16),
        workout_type="run",
        exercises=[],
        started_at=datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc),
    )
    repo.get = AsyncMock(return_value=session)

    planning_service = AsyncMock()
    service = WorkoutExecutionService(repo, planning_service)

    await service.finish_session("session1")

    assert repo.save.called
