"""Tests for SQLiteExecutionSession adapter."""

from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from forma.adapters.sqlite_execution_session import SQLiteExecutionSession
from forma.domain.execution_session import ExecutionExercise, ExecutionSession


@pytest.fixture
def db_path():
    """Create a temporary database for each test."""
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.db"


async def test_save_and_get_session(db_path):
    """Test saving and retrieving a session."""
    repo = SQLiteExecutionSession(db_path)
    session = ExecutionSession(
        session_id="session1",
        athlete_id="athlete1",
        date=date(2026, 3, 16),
        workout_type="run",
        exercises=[
            ExecutionExercise(id="warmup-0", phase="warmup", text="5 min jog"),
            ExecutionExercise(id="main-0", phase="main", text="3x10 squats"),
        ],
        started_at=datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc),
    )

    await repo.save(session)
    retrieved = await repo.get("session1")

    assert retrieved is not None
    assert retrieved.session_id == "session1"
    assert retrieved.athlete_id == "athlete1"
    assert retrieved.workout_type == "run"
    assert len(retrieved.exercises) == 2
    assert retrieved.exercises[0].id == "warmup-0"


async def test_get_nonexistent_session_returns_none(db_path):
    """Test that getting a nonexistent session returns None."""
    repo = SQLiteExecutionSession(db_path)

    retrieved = await repo.get("nonexistent")

    assert retrieved is None


async def test_save_updates_existing_session(db_path):
    """Test that saving a session with the same ID updates it."""
    repo = SQLiteExecutionSession(db_path)
    session1 = ExecutionSession(
        session_id="session1",
        athlete_id="athlete1",
        date=date(2026, 3, 16),
        workout_type="run",
        exercises=[ExecutionExercise(id="ex1", phase="main", text="run 5k")],
        started_at=datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc),
    )
    await repo.save(session1)

    # Mark exercise as completed and save again
    session1.exercises[0].completed = True
    await repo.save(session1)
    retrieved = await repo.get("session1")

    assert retrieved.exercises[0].completed is True


async def test_get_active_for_athlete_returns_incomplete_session(db_path):
    """Test that get_active_for_athlete returns an incomplete session."""
    repo = SQLiteExecutionSession(db_path)
    session = ExecutionSession(
        session_id="session1",
        athlete_id="athlete1",
        date=date(2026, 3, 16),
        workout_type="run",
        exercises=[],
        started_at=datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc),
    )
    await repo.save(session)

    active = await repo.get_active_for_athlete("athlete1")

    assert active is not None
    assert active.session_id == "session1"


async def test_get_active_for_athlete_ignores_completed_session(db_path):
    """Test that get_active_for_athlete ignores completed sessions."""
    repo = SQLiteExecutionSession(db_path)
    session = ExecutionSession(
        session_id="session1",
        athlete_id="athlete1",
        date=date(2026, 3, 16),
        workout_type="run",
        exercises=[],
        started_at=datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc),
        completed_at=datetime(2026, 3, 16, 10, 0, tzinfo=timezone.utc),
    )
    await repo.save(session)

    active = await repo.get_active_for_athlete("athlete1")

    assert active is None


async def test_get_active_for_athlete_returns_none_when_no_session(db_path):
    """Test that get_active_for_athlete returns None when no active session."""
    repo = SQLiteExecutionSession(db_path)

    active = await repo.get_active_for_athlete("athlete1")

    assert active is None
