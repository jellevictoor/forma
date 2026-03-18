"""PostgreSQL adapter for caching weekly workout plan output."""

import json
from datetime import date, datetime

from asyncpg import Pool

from forma.ports.plan_cache_repository import (
    CachedWeeklyPlan,
    PlannedDay,
    PlanCacheRepository,
    WeeklyPlan,
)


class PostgresPlanCache(PlanCacheRepository):
    """Persists weekly plan summaries in PostgreSQL."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def get(self, athlete_id: str) -> CachedWeeklyPlan | None:
        row = await self._pool.fetchrow(
            "SELECT * FROM plan_cache WHERE athlete_id = $1", athlete_id
        )
        if row is None:
            return None
        return self._row_to_cached_plan(row)

    async def save(
        self,
        athlete_id: str,
        plan: WeeklyPlan,
        latest_activity_at: datetime | None,
    ) -> None:
        await self._pool.execute(
            """
            INSERT INTO plan_cache (athlete_id, generated_at, latest_activity_at, data)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (athlete_id) DO UPDATE SET
                generated_at = EXCLUDED.generated_at,
                latest_activity_at = EXCLUDED.latest_activity_at,
                data = EXCLUDED.data
            """,
            athlete_id,
            plan.generated_at,
            latest_activity_at,
            self._serialize_plan(plan),
        )

    async def update_day_exercises(self, athlete_id: str, day: date, exercises: list[str]) -> None:
        row = await self._pool.fetchrow(
            "SELECT data FROM plan_cache WHERE athlete_id = $1", athlete_id
        )
        if row is None:
            return
        payload = json.loads(row["data"])
        day_str = day.isoformat()
        for d in payload["days"]:
            if d["day"] == day_str:
                d["exercises"] = exercises
                break
        await self._pool.execute(
            "UPDATE plan_cache SET data = $1 WHERE athlete_id = $2",
            json.dumps(payload),
            athlete_id,
        )

    async def invalidate(self, athlete_id: str) -> None:
        await self._pool.execute(
            "DELETE FROM plan_cache WHERE athlete_id = $1", athlete_id
        )

    def _serialize_plan(self, plan: WeeklyPlan) -> str:
        return json.dumps({
            "rationale": plan.rationale,
            "days": [
                {
                    "day": d.day.isoformat(),
                    "workout_type": d.workout_type,
                    "intensity": d.intensity,
                    "duration_minutes": d.duration_minutes,
                    "description": d.description,
                    "exercises": d.exercises,
                }
                for d in plan.days
            ],
        })

    def _row_to_cached_plan(self, row) -> CachedWeeklyPlan:
        payload = json.loads(row["data"])
        days = [
            PlannedDay(
                day=date.fromisoformat(d["day"]),
                workout_type=d["workout_type"],
                intensity=d["intensity"],
                duration_minutes=d["duration_minutes"],
                description=d["description"],
                exercises=d.get("exercises", {}),
            )
            for d in payload["days"]
        ]
        return CachedWeeklyPlan(
            days=days,
            rationale=payload["rationale"],
            generated_at=row["generated_at"],
            latest_activity_at=row["latest_activity_at"],
            is_stale=False,
        )
