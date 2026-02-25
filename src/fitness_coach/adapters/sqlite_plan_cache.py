"""SQLite adapter for caching weekly workout plan output."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from fitness_coach.ports.plan_cache_repository import (
    CachedWeeklyPlan,
    PlannedDay,
    PlanCacheRepository,
    WeeklyPlan,
)


class SQLitePlanCache(PlanCacheRepository):
    """Persists weekly plan summaries in SQLite."""

    def __init__(self, db_path: str | Path = "data/fitness_coach.db") -> None:
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
                CREATE TABLE IF NOT EXISTS plan_cache (
                    athlete_id TEXT PRIMARY KEY,
                    generated_at TEXT NOT NULL,
                    latest_activity_at TEXT,
                    data TEXT NOT NULL
                )
            """)

    async def get(self, athlete_id: str) -> CachedWeeklyPlan | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM plan_cache WHERE athlete_id = ?", (athlete_id,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_cached_plan(row)

    async def save(
        self,
        athlete_id: str,
        plan: WeeklyPlan,
        latest_activity_at: datetime | None,
    ) -> None:
        generated_at = plan.generated_at.isoformat()
        latest_at_str = latest_activity_at.isoformat() if latest_activity_at else None
        data = self._serialize_plan(plan)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO plan_cache (athlete_id, generated_at, latest_activity_at, data)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(athlete_id) DO UPDATE SET
                    generated_at = excluded.generated_at,
                    latest_activity_at = excluded.latest_activity_at,
                    data = excluded.data
                """,
                (athlete_id, generated_at, latest_at_str, data),
            )

    async def update_day_exercises(self, athlete_id: str, day: date, exercises: list[str]) -> None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data FROM plan_cache WHERE athlete_id = ?", (athlete_id,)
            ).fetchone()
        if row is None:
            return
        payload = json.loads(row["data"])
        day_str = day.isoformat()
        for d in payload["days"]:
            if d["day"] == day_str:
                d["exercises"] = exercises
                break
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE plan_cache SET data = ? WHERE athlete_id = ?",
                (json.dumps(payload), athlete_id),
            )

    async def invalidate(self, athlete_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM plan_cache WHERE athlete_id = ?", (athlete_id,))

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

    def _row_to_cached_plan(self, row: sqlite3.Row) -> CachedWeeklyPlan:
        generated_at = datetime.fromisoformat(row["generated_at"])
        latest_activity_at = (
            datetime.fromisoformat(row["latest_activity_at"])
            if row["latest_activity_at"]
            else None
        )
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
            generated_at=generated_at,
            latest_activity_at=latest_activity_at,
            is_stale=False,
        )
