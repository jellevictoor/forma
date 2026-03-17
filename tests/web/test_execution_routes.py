"""Tests for workout execution routes."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from forma.adapters.web.app import create_app
from forma.application.workout_execution_service import WorkoutExecutionService
from forma.domain.execution_session import ExecutionExercise, ExecutionSession


def make_execution_session() -> ExecutionSession:
    return ExecutionSession(
        session_id="session1",
        athlete_id="athlete1",
        date=date(2026, 3, 16),
        workout_type="run",
        exercises=[
            ExecutionExercise(id="warmup-0", phase="warmup", text="5 min jog", completed=False),
            ExecutionExercise(id="main-0", phase="main", text="3x10 squats", completed=False),
        ],
        started_at=datetime(2026, 3, 16, 9, 0, tzinfo=timezone.utc),
    )


def make_mock_execution_service() -> WorkoutExecutionService:
    service = AsyncMock(spec=WorkoutExecutionService)
    service.start_session = AsyncMock(return_value=make_execution_session())
    service.get_session = AsyncMock(return_value=make_execution_session())
    service.get_active_session = AsyncMock(return_value=None)
    service.complete_exercise = AsyncMock(return_value=make_execution_session())
    service.finish_session = AsyncMock(return_value=make_execution_session())
    return service


@pytest.fixture
def client():
    app = create_app()

    from forma.adapters.web.dependencies import (
        get_athlete_id,
        get_workout_execution_service,
    )

    app.dependency_overrides[get_athlete_id] = lambda: "athlete1"
    app.dependency_overrides[get_workout_execution_service] = lambda: make_mock_execution_service()

    return TestClient(app)


def test_post_start_session(client):
    """Test POST /api/execution/sessions starts a workout session."""
    response = client.post(
        "/api/execution/sessions",
        json={"date": "2026-03-16", "workout_type": "run"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["session_id"] == "session1"
    assert data["athlete_id"] == "athlete1"
    assert len(data["exercises"]) == 2


def test_post_start_session_response_format(client):
    """Test that session response includes all required fields."""
    response = client.post(
        "/api/execution/sessions",
        json={"date": "2026-03-16", "workout_type": "strength"},
    )

    data = response.json()
    assert "session_id" in data
    assert "athlete_id" in data
    assert "date" in data
    assert "workout_type" in data
    assert "exercises" in data
    assert "started_at" in data
    assert "completed_at" in data


def test_get_active_session_returns_none_initially(client):
    """Test GET /api/execution/sessions/active returns None when no active session."""
    response = client.get("/api/execution/sessions/active")

    assert response.status_code == 200
    assert response.json() is None


def test_get_session_by_id(client):
    """Test GET /api/execution/sessions/{session_id} retrieves a session."""
    response = client.get("/api/execution/sessions/session1")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "session1"


def test_post_complete_exercise(client):
    """Test POST /api/execution/sessions/{session_id}/exercises/{exercise_id}/complete marks exercise done."""
    response = client.post(
        "/api/execution/sessions/session1/exercises/warmup-0/complete"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "session1"


def test_post_finish_session(client):
    """Test POST /api/execution/sessions/{session_id}/finish ends a session."""
    response = client.post("/api/execution/sessions/session1/finish")

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "session1"


def test_session_json_exercise_structure(client):
    """Test that exercises are properly formatted in JSON response."""
    response = client.post(
        "/api/execution/sessions",
        json={"date": "2026-03-16", "workout_type": "run"},
    )

    data = response.json()
    exercise = data["exercises"][0]
    assert exercise["id"] == "warmup-0"
    assert exercise["phase"] == "warmup"
    assert exercise["text"] == "5 min jog"
    assert exercise["completed"] is False
