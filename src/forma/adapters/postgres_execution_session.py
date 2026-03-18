"""PostgreSQL adapter for workout execution sessions."""

import json
from datetime import datetime

from asyncpg import Pool

from forma.domain.execution_session import ExecutionExercise, ExecutionSession
from forma.ports.execution_session_repository import ExecutionSessionRepository


class PostgresExecutionSession(ExecutionSessionRepository):
    """Persists execution sessions in PostgreSQL."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def save(self, session: ExecutionSession) -> None:
        await self._pool.execute(
            """
            INSERT INTO execution_sessions (session_id, athlete_id, data)
            VALUES ($1, $2, $3)
            ON CONFLICT (session_id) DO UPDATE SET data = EXCLUDED.data
            """,
            session.session_id,
            session.athlete_id,
            self._serialize_session(session),
        )

    async def get(self, session_id: str) -> ExecutionSession | None:
        row = await self._pool.fetchrow(
            "SELECT * FROM execution_sessions WHERE session_id = $1", session_id
        )
        if row is None:
            return None
        return self._row_to_session(row)

    async def get_active_for_athlete(self, athlete_id: str) -> ExecutionSession | None:
        rows = await self._pool.fetch(
            "SELECT * FROM execution_sessions WHERE athlete_id = $1 ORDER BY session_id DESC",
            athlete_id,
        )
        for row in rows:
            session = self._row_to_session(row)
            if session.completed_at is None:
                return session
        return None

    def _serialize_session(self, session: ExecutionSession) -> str:
        return json.dumps({
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
        })

    def _row_to_session(self, row) -> ExecutionSession:
        data = json.loads(row["data"])
        return ExecutionSession(
            session_id=row["session_id"],
            athlete_id=row["athlete_id"],
            date=datetime.fromisoformat(data["date"]).date(),
            workout_type=data["workout_type"],
            exercises=[
                ExecutionExercise(
                    id=ex["id"],
                    phase=ex["phase"],
                    text=ex["text"],
                    completed=ex["completed"],
                )
                for ex in data["exercises"]
            ],
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data["completed_at"] else None,
        )
