"""PostgreSQL adapter for session tokens."""

import secrets
from datetime import datetime

from asyncpg import Pool

from forma.ports.session_repository import Session, SessionRepository

_TOKEN_BYTES = 32


class PostgresSessionRepository(SessionRepository):

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def get_by_token(self, token: str) -> Session | None:
        row = await self._pool.fetchrow(
            "SELECT token, athlete_id, expires_at FROM sessions"
            " WHERE token = $1 AND expires_at > NOW()",
            token,
        )
        if row is None:
            return None
        return Session(
            token=row["token"],
            athlete_id=row["athlete_id"],
            expires_at=row["expires_at"],
        )

    async def create(self, athlete_id: str, expires_at: datetime) -> Session:
        token = secrets.token_urlsafe(_TOKEN_BYTES)
        await self._pool.execute(
            "INSERT INTO sessions (token, athlete_id, expires_at) VALUES ($1, $2, $3)",
            token,
            athlete_id,
            expires_at,
        )
        return Session(token=token, athlete_id=athlete_id, expires_at=expires_at)

    async def delete(self, token: str) -> None:
        await self._pool.execute("DELETE FROM sessions WHERE token = $1", token)

    async def delete_all_for_athlete(self, athlete_id: str) -> None:
        await self._pool.execute(
            "DELETE FROM sessions WHERE athlete_id = $1", athlete_id
        )
