"""SQLite adapter for workout execution sessions."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from forma.domain.execution_session import ExecutionExercise, ExecutionSession
from forma.ports.execution_session_repository import ExecutionSessionRepository


class SQLiteExecutionSession(ExecutionSessionRepository):
    """Persists execution sessions in SQLite."""

    def __init__(self, db_path: str | Path = "data/forma.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS execution_sessions (
                    session_id TEXT PRIMARY KEY,
                    athlete_id TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            """)

    async def save(self, session: ExecutionSession) -> None:
        data = self._serialize_session(session)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO execution_sessions (session_id, athlete_id, data)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET data = excluded.data
                """,
                (session.session_id, session.athlete_id, data),
            )

    async def get(self, session_id: str) -> ExecutionSession | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM execution_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_session(row)

    async def get_active_for_athlete(self, athlete_id: str) -> ExecutionSession | None:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM execution_sessions WHERE athlete_id = ? ORDER BY session_id DESC",
                (athlete_id,),
            ).fetchall()
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

    def _row_to_session(self, row: sqlite3.Row) -> ExecutionSession:
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
