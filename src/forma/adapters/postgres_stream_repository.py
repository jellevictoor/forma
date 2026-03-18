"""PostgreSQL adapter for GPS stream caching."""

import json
from datetime import datetime, timezone

from asyncpg import Pool

from forma.ports.stream_repository import StreamRepository, WorkoutStreams


class PostgresStreamRepository(StreamRepository):
    """Persists GPS activity streams in PostgreSQL."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def get(self, workout_id: str) -> WorkoutStreams | None:
        row = await self._pool.fetchrow(
            "SELECT data FROM activity_streams WHERE workout_id = $1", workout_id
        )
        if not row:
            return None
        d = json.loads(row["data"])
        return WorkoutStreams(
            latlng=d["latlng"],
            time=d["time"],
            velocity_smooth=d["velocity_smooth"],
            heartrate=d.get("heartrate"),
        )

    async def save(self, workout_id: str, streams: WorkoutStreams) -> None:
        data = json.dumps({
            "latlng": streams.latlng,
            "time": streams.time,
            "velocity_smooth": streams.velocity_smooth,
            "heartrate": streams.heartrate,
        })
        await self._pool.execute(
            """
            INSERT INTO activity_streams (workout_id, fetched_at, data)
            VALUES ($1, $2, $3)
            ON CONFLICT (workout_id) DO UPDATE SET
                fetched_at = EXCLUDED.fetched_at,
                data = EXCLUDED.data
            """,
            workout_id,
            datetime.now(timezone.utc).isoformat(),
            data,
        )
