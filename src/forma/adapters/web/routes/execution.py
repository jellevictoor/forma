"""API routes for workout execution."""

from datetime import date

from fastapi import APIRouter, Depends, status

from forma.adapters.web.dependencies import (
    get_athlete_id,
    get_workout_execution_service,
)
from forma.application.workout_execution_service import WorkoutExecutionService
from forma.domain.execution_session import ExecutionSession

router = APIRouter(prefix="/api/execution", tags=["execution"])


def _session_to_json(session: ExecutionSession | None) -> dict | None:
    """Convert an ExecutionSession to JSON."""
    if session is None:
        return None
    return {
        "session_id": session.session_id,
        "athlete_id": session.athlete_id,
        "date": session.date.isoformat(),
        "workout_type": session.workout_type,
        "exercises": [
            {
                "id": ex.id,
                "phase": ex.phase,
                "text": ex.text,
                "completed": ex.completed,
            }
            for ex in session.exercises
        ],
        "started_at": session.started_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def start_session(
    payload: dict,
    athlete_id: str = Depends(get_athlete_id),
    service: WorkoutExecutionService = Depends(get_workout_execution_service),
) -> dict:
    """Start a new execution session for a workout."""
    date_str = payload.get("date")
    workout_type = payload.get("workout_type")

    date_obj = date.fromisoformat(date_str)
    session = await service.start_session(athlete_id, date_obj, workout_type)

    return _session_to_json(session)


@router.get("/sessions/active")
async def get_active_session(
    athlete_id: str = Depends(get_athlete_id),
    service: WorkoutExecutionService = Depends(get_workout_execution_service),
) -> dict | None:
    """Get the active (incomplete) session for an athlete."""
    session = await service.get_active_session(athlete_id)
    return _session_to_json(session)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    service: WorkoutExecutionService = Depends(get_workout_execution_service),
) -> dict:
    """Get a session by ID."""
    session = await service.get_session(session_id)
    if session is None:
        return {"error": "Not found"}
    return _session_to_json(session)


@router.post("/sessions/{session_id}/exercises/{exercise_id}/complete")
async def complete_exercise(
    session_id: str,
    exercise_id: str,
    service: WorkoutExecutionService = Depends(get_workout_execution_service),
) -> dict:
    """Mark an exercise as completed."""
    session = await service.complete_exercise(session_id, exercise_id)
    return _session_to_json(session)


@router.post("/sessions/{session_id}/finish")
async def finish_session(
    session_id: str,
    service: WorkoutExecutionService = Depends(get_workout_execution_service),
) -> dict:
    """Mark a session as completed."""
    session = await service.finish_session(session_id)
    return _session_to_json(session)
