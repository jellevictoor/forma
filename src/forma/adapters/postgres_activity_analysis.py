"""PostgreSQL adapter for caching per-workout AI analysis."""

import json
from datetime import datetime, timezone

from asyncpg import Pool

from forma.ports.activity_analysis_repository import (
    ActivityAnalysis,
    ActivityAnalysisRepository,
    CachedActivityAnalysis,
)


class PostgresActivityAnalysis(ActivityAnalysisRepository):
    """Persists per-workout AI analyses in PostgreSQL."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def get(self, workout_id: str) -> CachedActivityAnalysis | None:
        row = await self._pool.fetchrow(
            "SELECT * FROM activity_analysis_cache WHERE workout_id = $1", workout_id
        )
        if row is None:
            return None
        data = json.loads(row["data"])
        return CachedActivityAnalysis(
            workout_id=row["workout_id"],
            analysis=ActivityAnalysis(
                performance_assessment=data["performance_assessment"],
                training_load_context=data["training_load_context"],
                goal_relevance=data["goal_relevance"],
                comparison_to_recent=data["comparison_to_recent"],
                takeaway=data["takeaway"],
            ),
            generated_at=datetime.fromisoformat(row["generated_at"]),
        )

    async def save(self, workout_id: str, analysis: ActivityAnalysis) -> None:
        generated_at = datetime.now(tz=timezone.utc).isoformat()
        data = json.dumps({
            "performance_assessment": analysis.performance_assessment,
            "training_load_context": analysis.training_load_context,
            "goal_relevance": analysis.goal_relevance,
            "comparison_to_recent": analysis.comparison_to_recent,
            "takeaway": analysis.takeaway,
        })
        await self._pool.execute(
            """
            INSERT INTO activity_analysis_cache (workout_id, generated_at, data)
            VALUES ($1, $2, $3)
            ON CONFLICT (workout_id) DO UPDATE SET
                generated_at = EXCLUDED.generated_at,
                data = EXCLUDED.data
            """,
            workout_id,
            generated_at,
            data,
        )

    async def invalidate(self, workout_id: str) -> None:
        await self._pool.execute(
            "DELETE FROM activity_analysis_cache WHERE workout_id = $1", workout_id
        )
