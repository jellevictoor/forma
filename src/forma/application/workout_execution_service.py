"""Service for managing workout execution sessions."""

import uuid
from datetime import date, datetime, timezone

from forma.domain.execution_session import ExecutionExercise, ExecutionSession
from forma.ports.execution_session_repository import ExecutionSessionRepository


class WorkoutExecutionService:
    """Manages active workout execution sessions."""

    def __init__(
        self,
        session_repo: ExecutionSessionRepository,
        planning_service: object,  # Would be WorkoutPlanningService, but avoid circular import
    ) -> None:
        self._sessions = session_repo
        self._planning = planning_service

    async def start_session(
        self,
        athlete_id: str,
        date_: date,
        workout_type: str,
    ) -> ExecutionSession:
        """Start a new execution session, fetching exercises from the plan cache."""
        exercises_by_phase = await self._planning.get_exercises_for_day(athlete_id, date_)

        exercises = []
        for phase in ["warmup", "main", "cooldown"]:
            if phase not in exercises_by_phase:
                continue
            for idx, text in enumerate(exercises_by_phase[phase]):
                exercises.append(
                    ExecutionExercise(
                        id=f"{phase}-{idx}",
                        phase=phase,
                        text=text,
                    )
                )

        session = ExecutionSession(
            session_id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            date=date_,
            workout_type=workout_type,
            exercises=exercises,
            started_at=datetime.now(tz=timezone.utc),
        )
        await self._sessions.save(session)
        return session

    async def get_session(self, session_id: str) -> ExecutionSession | None:
        """Retrieve a session by ID."""
        return await self._sessions.get(session_id)

    async def get_active_session(self, athlete_id: str) -> ExecutionSession | None:
        """Retrieve the active (incomplete) session for an athlete."""
        return await self._sessions.get_active_for_athlete(athlete_id)

    async def complete_exercise(self, session_id: str, exercise_id: str) -> ExecutionSession:
        """Mark an exercise as completed and save."""
        session = await self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        session.complete_exercise(exercise_id)
        await self._sessions.save(session)
        return session

    async def finish_session(self, session_id: str) -> ExecutionSession:
        """Mark a session as completed and save."""
        session = await self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        session.complete(datetime.now(tz=timezone.utc))
        await self._sessions.save(session)
        return session
