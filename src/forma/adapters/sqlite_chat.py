"""SQLite adapter for persisting per-workout chat messages."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from forma.ports.chat_repository import ChatMessage, ChatRepository


class SQLiteChat(ChatRepository):
    """Persists workout chat messages in SQLite."""

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
                CREATE TABLE IF NOT EXISTS activity_chat (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workout_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

    async def list_messages(self, workout_id: str) -> list[ChatMessage]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT role, content, created_at FROM activity_chat WHERE workout_id = ? ORDER BY id",
                (workout_id,),
            ).fetchall()
        return [
            ChatMessage(
                role=row["role"],
                content=row["content"],
                created_at=datetime.fromisoformat(row["created_at"]),
            )
            for row in rows
        ]

    async def append_message(self, workout_id: str, role: str, content: str) -> None:
        created_at = datetime.now(tz=timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO activity_chat (workout_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (workout_id, role, content, created_at),
            )

    async def clear_messages(self, workout_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM activity_chat WHERE workout_id = ?", (workout_id,))
