"""SQLite adapter for caching per-workout AI analysis."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from forma.ports.activity_analysis_repository import (
    ActivityAnalysis,
    ActivityAnalysisRepository,
    CachedActivityAnalysis,
)


class SQLiteActivityAnalysis(ActivityAnalysisRepository):
    """Persists per-workout AI analyses in SQLite."""

    def __init__(self, db_path: str | Path = "data/forma.db") -> None:
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
                CREATE TABLE IF NOT EXISTS activity_analysis_cache (
                    workout_id TEXT PRIMARY KEY,
                    generated_at TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            """)

    async def get(self, workout_id: str) -> CachedActivityAnalysis | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM activity_analysis_cache WHERE workout_id = ?",
                (workout_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_cached(row)

    async def save(self, workout_id: str, analysis: ActivityAnalysis) -> None:
        generated_at = datetime.now(tz=timezone.utc).isoformat()
        data = json.dumps({
            "performance_assessment": analysis.performance_assessment,
            "training_load_context": analysis.training_load_context,
            "goal_relevance": analysis.goal_relevance,
            "comparison_to_recent": analysis.comparison_to_recent,
            "takeaway": analysis.takeaway,
        })
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO activity_analysis_cache (workout_id, generated_at, data)
                VALUES (?, ?, ?)
                ON CONFLICT(workout_id) DO UPDATE SET
                    generated_at = excluded.generated_at,
                    data = excluded.data
                """,
                (workout_id, generated_at, data),
            )

    async def invalidate(self, workout_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM activity_analysis_cache WHERE workout_id = ?",
                (workout_id,),
            )

    def _row_to_cached(self, row: sqlite3.Row) -> CachedActivityAnalysis:
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
