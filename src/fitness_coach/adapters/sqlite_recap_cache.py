"""SQLite adapter for caching weekly recap output."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from fitness_coach.ports.recap_cache_repository import CachedRecap, RecapCacheRepository, WeeklyRecap


class SQLiteRecapCache(RecapCacheRepository):
    """Persists weekly recap summaries in SQLite."""

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
                CREATE TABLE IF NOT EXISTS recap_cache (
                    athlete_id TEXT PRIMARY KEY,
                    generated_at TEXT NOT NULL,
                    latest_activity_at TEXT,
                    summary TEXT NOT NULL,
                    highlight TEXT NOT NULL,
                    form_note TEXT NOT NULL,
                    focus TEXT NOT NULL
                )
            """)

    async def get(self, athlete_id: str) -> CachedRecap | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM recap_cache WHERE athlete_id = ?", (athlete_id,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_cached_recap(row)

    async def save(
        self,
        athlete_id: str,
        recap: WeeklyRecap,
        latest_activity_at: datetime | None,
    ) -> None:
        generated_at = datetime.now(tz=timezone.utc).isoformat()
        latest_at_str = latest_activity_at.isoformat() if latest_activity_at else None
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO recap_cache
                    (athlete_id, generated_at, latest_activity_at, summary, highlight, form_note, focus)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(athlete_id) DO UPDATE SET
                    generated_at = excluded.generated_at,
                    latest_activity_at = excluded.latest_activity_at,
                    summary = excluded.summary,
                    highlight = excluded.highlight,
                    form_note = excluded.form_note,
                    focus = excluded.focus
                """,
                (
                    athlete_id,
                    generated_at,
                    latest_at_str,
                    recap.summary,
                    recap.highlight,
                    recap.form_note,
                    json.dumps(recap.focus),
                ),
            )

    def _row_to_cached_recap(self, row: sqlite3.Row) -> CachedRecap:
        generated_at = datetime.fromisoformat(row["generated_at"])
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
            generated_at=generated_at,
            latest_activity_at=latest_activity_at,
        )
