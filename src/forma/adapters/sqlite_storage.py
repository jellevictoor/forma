"""SQLite storage adapter for persistent data."""

import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterator

from forma.domain.athlete import Athlete
from forma.domain.weight_entry import WeightEntry
from forma.domain.workout import Workout
from forma.ports.athlete_repository import AthleteRepository
from forma.ports.weight_repository import WeightRepository
from forma.ports.workout_repository import WorkoutRepository


class SQLiteStorage(AthleteRepository, WorkoutRepository, WeightRepository):
    """SQLite-based storage for all domain entities."""

    def __init__(self, db_path: str | Path = "data/forma.db"):
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
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS athletes (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    is_default INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS workouts (
                    id TEXT PRIMARY KEY,
                    athlete_id TEXT NOT NULL,
                    strava_id INTEGER,
                    start_time TEXT NOT NULL,
                    workout_type TEXT,
                    data TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
                );

                CREATE INDEX IF NOT EXISTS idx_workouts_athlete_id ON workouts(athlete_id);
                CREATE INDEX IF NOT EXISTS idx_workouts_strava_id ON workouts(strava_id);
                CREATE INDEX IF NOT EXISTS idx_workouts_start_time ON workouts(start_time);

                CREATE TABLE IF NOT EXISTS weight_entries (
                    id TEXT PRIMARY KEY,
                    athlete_id TEXT NOT NULL,
                    weight_kg REAL NOT NULL,
                    recorded_at TEXT NOT NULL,
                    notes TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (athlete_id) REFERENCES athletes(id)
                );

                CREATE INDEX IF NOT EXISTS idx_weight_entries_athlete_id ON weight_entries(athlete_id);
                CREATE INDEX IF NOT EXISTS idx_weight_entries_recorded_at ON weight_entries(recorded_at);
            """)
            self._migrate_workout_type_column(conn)

    def _migrate_workout_type_column(self, conn: sqlite3.Connection) -> None:
        columns = [row[1] for row in conn.execute("PRAGMA table_info(workouts)").fetchall()]
        if "workout_type" not in columns:
            conn.execute("ALTER TABLE workouts ADD COLUMN workout_type TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_workouts_workout_type ON workouts(workout_type)"
        )

    def _serialize_athlete(self, athlete: Athlete) -> str:
        return athlete.model_dump_json()

    def _deserialize_athlete(self, data: str) -> Athlete:
        return Athlete.model_validate_json(data)

    def _serialize_workout(self, workout: Workout) -> str:
        return workout.model_dump_json()

    def _deserialize_workout(self, data: str) -> Workout:
        return Workout.model_validate_json(data)

    # AthleteRepository implementation

    async def get(self, athlete_id: str) -> Athlete | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data FROM athletes WHERE id = ?", (athlete_id,)
            ).fetchone()
            if row:
                return self._deserialize_athlete(row["data"])
            return None

    async def save(self, athlete: Athlete) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO athletes (id, data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    data = excluded.data,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (athlete.id, self._serialize_athlete(athlete)),
            )

    async def delete(self, athlete_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM athletes WHERE id = ?", (athlete_id,))

    async def get_default(self) -> Athlete | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data FROM athletes WHERE is_default = 1"
            ).fetchone()
            if row:
                return self._deserialize_athlete(row["data"])
            row = conn.execute(
                "SELECT data FROM athletes ORDER BY created_at LIMIT 1"
            ).fetchone()
            if row:
                return self._deserialize_athlete(row["data"])
            return None

    async def set_default(self, athlete_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("UPDATE athletes SET is_default = 0")
            conn.execute(
                "UPDATE athletes SET is_default = 1 WHERE id = ?", (athlete_id,)
            )

    # WorkoutRepository implementation

    async def get_workout(self, workout_id: str) -> Workout | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data FROM workouts WHERE id = ?", (workout_id,)
            ).fetchone()
            if row:
                return self._deserialize_workout(row["data"])
            return None

    async def get_workout_by_strava_id(self, strava_id: int) -> Workout | None:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data FROM workouts WHERE strava_id = ?", (strava_id,)
            ).fetchone()
            if row:
                return self._deserialize_workout(row["data"])
            return None

    async def save_workout(self, workout: Workout) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO workouts (id, athlete_id, strava_id, start_time, workout_type, data)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    data = excluded.data,
                    workout_type = excluded.workout_type
                """,
                (
                    workout.id,
                    workout.athlete_id,
                    workout.strava_id,
                    workout.start_time.isoformat(),
                    workout.workout_type.value,
                    self._serialize_workout(workout),
                ),
            )

    async def delete_workout(self, workout_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))

    async def list_workouts_for_athlete(
        self,
        athlete_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> list[Workout]:
        with self._get_connection() as conn:
            query = "SELECT data FROM workouts WHERE athlete_id = ?"
            params: list = [athlete_id]

            if start_date:
                query += " AND start_time >= ?"
                params.append(start_date.isoformat())
            if end_date:
                query += " AND start_time <= ?"
                params.append(end_date.isoformat())

            query += " ORDER BY start_time DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [self._deserialize_workout(row["data"]) for row in rows]

    async def get_recent(self, athlete_id: str, count: int = 10) -> list[Workout]:
        return await self.list_workouts_for_athlete(athlete_id, limit=count)

    # WeightRepository implementation

    async def save_weight_entry(self, entry: WeightEntry) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO weight_entries (id, athlete_id, weight_kg, recorded_at, notes)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    weight_kg = excluded.weight_kg,
                    recorded_at = excluded.recorded_at,
                    notes = excluded.notes
                """,
                (entry.id, entry.athlete_id, entry.weight_kg, entry.recorded_at.isoformat(), entry.notes),
            )

    async def list_weight_entries(self, athlete_id: str, limit: int = 90) -> list[WeightEntry]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, athlete_id, weight_kg, recorded_at, notes
                FROM weight_entries
                WHERE athlete_id = ?
                ORDER BY recorded_at DESC
                LIMIT ?
                """,
                (athlete_id, limit),
            ).fetchall()
            return [self._row_to_weight_entry(row) for row in rows]

    async def get_latest_weight(self, athlete_id: str) -> WeightEntry | None:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, athlete_id, weight_kg, recorded_at, notes
                FROM weight_entries
                WHERE athlete_id = ?
                ORDER BY recorded_at DESC
                LIMIT 1
                """,
                (athlete_id,),
            ).fetchone()
            if row:
                return self._row_to_weight_entry(row)
            return None

    async def delete_weight_entry(self, entry_id: str) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM weight_entries WHERE id = ?", (entry_id,))

    def _row_to_weight_entry(self, row: sqlite3.Row) -> WeightEntry:
        return WeightEntry(
            id=row["id"],
            athlete_id=row["athlete_id"],
            weight_kg=row["weight_kg"],
            recorded_at=date.fromisoformat(row["recorded_at"]),
            notes=row["notes"] or "",
        )
