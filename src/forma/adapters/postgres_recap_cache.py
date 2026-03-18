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
        data = json.loads(row["data"])
        return CachedRecap(
            summary=data["summary"],
            highlight=data["highlight"],
            form_note=data["form_note"],
            focus=data["focus"],
            generated_at=row["generated_at"],
            latest_activity_at=row["latest_activity_at"],
        )

    async def save(
        self,
        athlete_id: str,
        recap: WeeklyRecap,
        latest_activity_at: datetime | None,
    ) -> None:
        data = json.dumps({
            "summary": recap.summary,
            "highlight": recap.highlight,
            "form_note": recap.form_note,
            "focus": recap.focus,
        })
        await self._pool.execute(
            """
            INSERT INTO recap_cache (athlete_id, generated_at, latest_activity_at, data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (athlete_id) DO UPDATE SET
                generated_at = EXCLUDED.generated_at,
                latest_activity_at = EXCLUDED.latest_activity_at,
                data = EXCLUDED.data
            """,
            athlete_id,
            datetime.now(tz=timezone.utc),
            latest_activity_at,
            data,
        )
