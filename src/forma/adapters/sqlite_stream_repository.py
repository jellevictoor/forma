"""SQLite adapter for GPS stream caching."""

import json
from datetime import datetime, timezone

import aiosqlite

from forma.ports.stream_repository import StreamRepository, WorkoutStreams


class SQLiteStreamRepository(StreamRepository):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def _ensure_table(self, conn: aiosqlite.Connection) -> None:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS activity_streams (
                workout_id TEXT PRIMARY KEY,
                fetched_at TEXT NOT NULL,
                data TEXT NOT NULL
            )
        """)

    async def get(self, workout_id: str) -> WorkoutStreams | None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_table(conn)
            async with conn.execute(
                "SELECT data FROM activity_streams WHERE workout_id = ?",
                (workout_id,),
            ) as cursor:
                row = await cursor.fetchone()
        if not row:
            return None
        d = json.loads(row[0])
        return WorkoutStreams(
            latlng=d["latlng"],
            time=d["time"],
            velocity_smooth=d["velocity_smooth"],
            heartrate=d.get("heartrate"),
        )

    async def save(self, workout_id: str, streams: WorkoutStreams) -> None:
        data = {
            "latlng": streams.latlng,
            "time": streams.time,
            "velocity_smooth": streams.velocity_smooth,
            "heartrate": streams.heartrate,
        }
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_table(conn)
            await conn.execute(
                """
                INSERT OR REPLACE INTO activity_streams (workout_id, fetched_at, data)
                VALUES (?, ?, ?)
                """,
                (workout_id, datetime.now(timezone.utc).isoformat(), json.dumps(data)),
            )
            await conn.commit()
