"""SQLite adapter for caching training insights output."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from forma.ports.insights_cache_repository import CachedInsights, InsightsCacheRepository


class SQLiteInsightsCache(InsightsCacheRepository):
    """Persists training insights in SQLite."""

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
                CREATE TABLE IF NOT EXISTS insights_cache (
                    athlete_id TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    generated_at TEXT NOT NULL,
                    data TEXT NOT NULL,
                    PRIMARY KEY (athlete_id, year)
                )
            """)

    async def get(self, athlete_id: str, year: int) -> CachedInsights | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM insights_cache WHERE athlete_id = ? AND year = ?",
                (athlete_id, year),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_cached(row)

    async def save(self, athlete_id: str, year: int, insights) -> None:
        generated_at = datetime.now(tz=timezone.utc).isoformat()
        data = json.dumps({
            "summary": insights.summary,
            "patterns": insights.patterns,
            "impact": insights.impact,
            "recommendations": insights.recommendations,
            "note_count": insights.note_count,
        })
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO insights_cache (athlete_id, year, generated_at, data)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(athlete_id, year) DO UPDATE SET
                    generated_at = excluded.generated_at,
                    data = excluded.data
                """,
                (athlete_id, year, generated_at, data),
            )

    def _row_to_cached(self, row: sqlite3.Row) -> CachedInsights:
        data = json.loads(row["data"])
        return CachedInsights(
            summary=data["summary"],
            patterns=data["patterns"],
            impact=data["impact"],
            recommendations=data["recommendations"],
            note_count=data["note_count"],
            generated_at=datetime.fromisoformat(row["generated_at"]),
            year=row["year"],
        )
