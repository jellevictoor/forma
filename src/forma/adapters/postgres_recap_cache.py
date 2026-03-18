"""PostgreSQL adapter for caching weekly recap output."""

import json
from datetime import datetime, timezone

from asyncpg import Pool

from forma.ports.recap_cache_repository import CachedRecap, RecapCacheRepository, WeeklyRecap


class PostgresRecapCache(RecapCacheRepository):
    """Persists weekly recap summaries in PostgreSQL."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def get(self, athlete_id: str) -> CachedRecap | None:
        row = await self._pool.fetchrow(
            "SELECT * FROM recap_cache WHERE athlete_id = $1", athlete_id
        )
        if row is None:
            return None
        latest_activity_at = (
            datetime.fromisoformat(row["latest_activity_at"])
            if row["latest_activity_at"]
            else None
        )
        return CachedRecap(
            summary=row["summary"],
            highlight=row["highlight"],
            form_note=row["form_note"],
            focus=json.loads(row["focus"]),
            generated_at=datetime.fromisoformat(row["generated_at"]),
            latest_activity_at=latest_activity_at,
        )

    async def save(
        self,
        athlete_id: str,
        recap: WeeklyRecap,
        latest_activity_at: datetime | None,
    ) -> None:
        generated_at = datetime.now(tz=timezone.utc).isoformat()
        latest_at_str = latest_activity_at.isoformat() if latest_activity_at else None
        await self._pool.execute(
            """
            INSERT INTO recap_cache
                (athlete_id, generated_at, latest_activity_at, summary, highlight, form_note, focus)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (athlete_id) DO UPDATE SET
                generated_at = EXCLUDED.generated_at,
                latest_activity_at = EXCLUDED.latest_activity_at,
                summary = EXCLUDED.summary,
                highlight = EXCLUDED.highlight,
                form_note = EXCLUDED.form_note,
                focus = EXCLUDED.focus
            """,
            athlete_id,
            generated_at,
            latest_at_str,
            recap.summary,
            recap.highlight,
            recap.form_note,
            json.dumps(recap.focus),
        )
