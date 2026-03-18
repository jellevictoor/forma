"""PostgreSQL adapter for per-workout chat messages."""

from datetime import datetime, timezone

from asyncpg import Pool

from forma.ports.chat_repository import ChatMessage, ChatRepository


class PostgresChat(ChatRepository):
    """Persists workout chat messages in PostgreSQL."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def list_messages(self, workout_id: str) -> list[ChatMessage]:
        rows = await self._pool.fetch(
            "SELECT role, content, created_at FROM activity_chat WHERE workout_id = $1 ORDER BY id",
            workout_id,
        )
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
        await self._pool.execute(
            "INSERT INTO activity_chat (workout_id, role, content, created_at) VALUES ($1, $2, $3, $4)",
            workout_id,
            role,
            content,
            created_at,
        )

    async def clear_messages(self, workout_id: str) -> None:
        await self._pool.execute(
            "DELETE FROM activity_chat WHERE workout_id = $1", workout_id
        )
