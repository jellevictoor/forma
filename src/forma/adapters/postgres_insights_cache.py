"""PostgreSQL adapter for caching training insights output."""

import json
from datetime import datetime, timezone

from asyncpg import Pool

from forma.ports.insights_cache_repository import CachedInsights, InsightsCacheRepository


class PostgresInsightsCache(InsightsCacheRepository):
    """Persists training insights in PostgreSQL."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def get(self, athlete_id: str, year: int) -> CachedInsights | None:
        row = await self._pool.fetchrow(
            "SELECT * FROM insights_cache WHERE athlete_id = $1 AND year = $2",
            athlete_id,
            year,
        )
        if row is None:
            return None
        data = json.loads(row["data"])
        return CachedInsights(
            summary=data["summary"],
            patterns=data["patterns"],
            impact=data["impact"],
            recommendations=data["recommendations"],
            note_count=data["note_count"],
            generated_at=row["generated_at"],
            year=row["year"],
        )

    async def save(self, athlete_id: str, year: int, insights) -> None:
        generated_at = datetime.now(tz=timezone.utc)
        data = json.dumps({
            "summary": insights.summary,
            "patterns": insights.patterns,
            "impact": insights.impact,
            "recommendations": insights.recommendations,
            "note_count": insights.note_count,
        })
        await self._pool.execute(
            """
            INSERT INTO insights_cache (athlete_id, year, generated_at, data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (athlete_id, year) DO UPDATE SET
                generated_at = EXCLUDED.generated_at,
                data = EXCLUDED.data
            """,
            athlete_id,
            year,
            generated_at,
            data,
        )
