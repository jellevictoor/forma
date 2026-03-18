"""SQLite read-side adapter for workout analytics queries."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Iterator

from forma.domain.workout import Workout
from forma.ports.workout_analytics_repository import (
    PersonalRecord,
    SportSummary,
    WeeklyVolume,
    WorkoutAnalyticsRepository,
)


class SQLiteAnalyticsRepository(WorkoutAnalyticsRepository):
    """Read-side SQLite adapter — performs aggregation queries over the workouts table."""

    def __init__(self, db_path: str | Path = "data/forma.db"):
        self._db_path = Path(db_path)

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _year_range(self, year: int) -> tuple[str, str]:
        start = date(year, 1, 1).isoformat()
        end = date(year, 12, 31).isoformat()
        return start, end

    async def weekly_volume(
        self,
        athlete_id: str,
        workout_type: str | None,
        year: int,
    ) -> list[WeeklyVolume]:
        year_start, year_end = self._year_range(year)

        query = """
            SELECT
                date(start_time, 'weekday 0', '-6 days') AS week_start,
                workout_type,
                SUM(CAST(json_extract(data, '$.distance_meters') AS REAL)) AS total_distance,
                SUM(CAST(json_extract(data, '$.duration_seconds') AS INTEGER)) AS total_duration,
                COUNT(*) AS workout_count
            FROM workouts
            WHERE athlete_id = ?
              AND start_time >= ?
              AND start_time <= ?
        """
        params: list = [athlete_id, year_start, year_end]

        if workout_type:
            query += " AND workout_type = ?"
            params.append(workout_type)

        query += " GROUP BY week_start, workout_type ORDER BY week_start"

        with self._connection() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            WeeklyVolume(
                week_start=date.fromisoformat(row["week_start"]),
                total_distance_meters=row["total_distance"] or 0.0,
                total_duration_seconds=row["total_duration"] or 0,
                workout_count=row["workout_count"],
                workout_type=row["workout_type"],
            )
            for row in rows
        ]

    async def weekly_volume_for_range(
        self,
        athlete_id: str,
        since: date,
        until: date,
    ) -> list[WeeklyVolume]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    date(start_time, 'weekday 0', '-6 days') AS week_start,
                    workout_type,
                    SUM(CAST(json_extract(data, '$.distance_meters') AS REAL)) AS total_distance,
                    SUM(CAST(json_extract(data, '$.duration_seconds') AS INTEGER)) AS total_duration,
                    COUNT(*) AS workout_count
                FROM workouts
                WHERE athlete_id = ?
                  AND start_time >= ?
                  AND start_time <= ?
                GROUP BY week_start, workout_type
                ORDER BY week_start
                """,
                (athlete_id, since.isoformat(), until.isoformat()),
            ).fetchall()

        return [
            WeeklyVolume(
                week_start=date.fromisoformat(row["week_start"]),
                total_distance_meters=row["total_distance"] or 0.0,
                total_duration_seconds=row["total_duration"] or 0,
                workout_count=row["workout_count"],
                workout_type=row["workout_type"],
            )
            for row in rows
        ]

    async def personal_records_for_run(
        self,
        athlete_id: str,
        distances_meters: list[float],
    ) -> list[PersonalRecord]:
        records: list[PersonalRecord] = []

        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT id, start_time, data
                FROM workouts
                WHERE athlete_id = ? AND workout_type = 'run'
                  AND json_extract(data, '$.distance_meters') IS NOT NULL
                  AND json_extract(data, '$.moving_time_seconds') IS NOT NULL
                ORDER BY start_time
                """,
                (athlete_id,),
            ).fetchall()

        workouts = [
            (row["id"], date.fromisoformat(row["start_time"][:10]), Workout.model_validate_json(row["data"]))
            for row in rows
        ]

        for bucket in distances_meters:
            best = self._best_effort_for_distance(workouts, bucket)
            if best:
                records.append(best)

        return records

    def _best_effort_for_distance(
        self,
        workouts: list[tuple[str, date, Workout]],
        min_distance: float,
    ) -> PersonalRecord | None:
        candidates = [
            (workout_id, achieved_on, w)
            for workout_id, achieved_on, w in workouts
            if w.distance_meters and w.distance_meters >= min_distance and w.moving_time_seconds
        ]

        if not candidates:
            return None

        best_id, best_date, best = min(candidates, key=lambda t: t[2].moving_time_seconds or float("inf"))
        pace = (best.moving_time_seconds / 60) / (best.distance_meters / 1000) if best.distance_meters else 0.0

        return PersonalRecord(
            workout_type="run",
            distance_meters=min_distance,
            duration_seconds=best.moving_time_seconds or best.duration_seconds,
            pace_min_per_km=pace,
            achieved_on=best_date,
            workout_id=best_id,
        )

    async def pace_trend(
        self,
        athlete_id: str,
        workout_type: str,
        year: int,
    ) -> list[dict]:
        year_start, year_end = self._year_range(year)

        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    date(start_time, 'weekday 0', '-6 days') AS week_start,
                    AVG(
                        CAST(json_extract(data, '$.moving_time_seconds') AS REAL) / 60.0
                        / (CAST(json_extract(data, '$.distance_meters') AS REAL) / 1000.0)
                    ) AS pace_min_per_km
                FROM workouts
                WHERE athlete_id = ?
                  AND workout_type = ?
                  AND start_time >= ? AND start_time <= ?
                  AND json_extract(data, '$.distance_meters') > 0
                  AND json_extract(data, '$.moving_time_seconds') > 0
                GROUP BY week_start
                ORDER BY week_start
                """,
                (athlete_id, workout_type, year_start, year_end),
            ).fetchall()

        return [
            {"week_start": row["week_start"], "pace_min_per_km": row["pace_min_per_km"]}
            for row in rows
        ]

    async def pace_trend_for_range(
        self,
        athlete_id: str,
        workout_type: str,
        since: date,
        until: date,
    ) -> list[dict]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    date(start_time, 'weekday 0', '-6 days') AS week_start,
                    AVG(
                        CAST(json_extract(data, '$.moving_time_seconds') AS REAL) / 60.0
                        / (CAST(json_extract(data, '$.distance_meters') AS REAL) / 1000.0)
                    ) AS pace_min_per_km
                FROM workouts
                WHERE athlete_id = ?
                  AND workout_type = ?
                  AND start_time >= ? AND start_time <= ?
                  AND json_extract(data, '$.distance_meters') > 0
                  AND json_extract(data, '$.moving_time_seconds') > 0
                GROUP BY week_start
                ORDER BY week_start
                """,
                (athlete_id, workout_type, since.isoformat(), until.isoformat()),
            ).fetchall()

        return [
            {"week_start": row["week_start"], "pace_min_per_km": row["pace_min_per_km"]}
            for row in rows
        ]

    async def sport_summaries(self, athlete_id: str, year: int) -> list[SportSummary]:
        year_start, year_end = self._year_range(year)

        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    workout_type,
                    COUNT(*) AS total_workouts,
                    SUM(CAST(json_extract(data, '$.distance_meters') AS REAL)) AS total_distance,
                    SUM(CAST(json_extract(data, '$.duration_seconds') AS INTEGER)) AS total_duration,
                    MAX(date(start_time)) AS most_recent
                FROM workouts
                WHERE athlete_id = ?
                  AND workout_type IS NOT NULL
                  AND start_time >= ? AND start_time <= ?
                GROUP BY workout_type
                ORDER BY total_workouts DESC
                """,
                (athlete_id, year_start, year_end),
            ).fetchall()

        return [
            SportSummary(
                workout_type=row["workout_type"],
                total_workouts=row["total_workouts"],
                total_distance_meters=row["total_distance"] or 0.0,
                total_duration_seconds=row["total_duration"] or 0,
                most_recent=date.fromisoformat(row["most_recent"]) if row["most_recent"] else None,
            )
            for row in rows
        ]

    async def list_workouts_paginated(
        self,
        athlete_id: str,
        workout_type: str | None,
        page: int,
        page_size: int,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list[Workout], int]:
        offset = (page - 1) * page_size

        where = "athlete_id = ?"
        params: list = [athlete_id]

        if date_from:
            where += " AND date(start_time) >= ?"
            params.append(date_from.isoformat())
        if date_to:
            where += " AND date(start_time) <= ?"
            params.append(date_to.isoformat())
        if workout_type and workout_type != "all":
            where += " AND workout_type = ?"
            params.append(workout_type)

        with self._connection() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM workouts WHERE {where}", params
            ).fetchone()[0]

            rows = conn.execute(
                f"SELECT data FROM workouts WHERE {where} ORDER BY start_time DESC LIMIT ? OFFSET ?",
                params + [page_size, offset],
            ).fetchall()

        workouts = [Workout.model_validate_json(row["data"]) for row in rows]
        return workouts, total

    async def strength_frequency(
        self,
        athlete_id: str,
        year: int,
    ) -> list[dict]:
        year_start, year_end = self._year_range(year)

        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    date(start_time, 'weekday 0', '-6 days') AS week_start,
                    COUNT(*) AS count
                FROM workouts
                WHERE athlete_id = ?
                  AND workout_type = 'strength'
                  AND start_time >= ? AND start_time <= ?
                GROUP BY week_start
                ORDER BY week_start
                """,
                (athlete_id, year_start, year_end),
            ).fetchall()

        return [{"week_start": row["week_start"], "count": row["count"]} for row in rows]

    async def climbing_sessions(self, athlete_id: str, year: int) -> list[dict]:
        year_start, year_end = self._year_range(year)

        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT id, start_time, data
                FROM workouts
                WHERE athlete_id = ? AND workout_type = 'climbing'
                  AND start_time >= ? AND start_time <= ?
                ORDER BY start_time DESC
                """,
                (athlete_id, year_start, year_end),
            ).fetchall()

        return [
            {
                "id": row["id"],
                "date": row["start_time"][:10],
                "duration_seconds": json.loads(row["data"]).get("duration_seconds", 0),
                "name": json.loads(row["data"]).get("name", ""),
            }
            for row in rows
        ]

    async def sport_stats_for_month(self, athlete_id: str, year: int, month: int) -> list[dict]:
        start = date(year, month, 1).isoformat()
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        end = date(next_year, next_month, 1).isoformat()

        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    workout_type,
                    COUNT(*) AS sessions,
                    SUM(CAST(json_extract(data, '$.distance_meters') AS REAL)) AS total_distance,
                    SUM(CAST(json_extract(data, '$.duration_seconds') AS INTEGER)) AS total_duration,
                    AVG(
                        CASE WHEN json_extract(data, '$.distance_meters') > 0
                                  AND json_extract(data, '$.moving_time_seconds') > 0
                             THEN CAST(json_extract(data, '$.moving_time_seconds') AS REAL) / 60.0
                                  / (json_extract(data, '$.distance_meters') / 1000.0)
                        END
                    ) AS avg_pace
                FROM workouts
                WHERE athlete_id = ?
                  AND date(start_time) >= ? AND date(start_time) < ?
                  AND workout_type IS NOT NULL
                GROUP BY workout_type
                ORDER BY workout_type
                """,
                (athlete_id, start, end),
            ).fetchall()

        return [
            {
                "workout_type": row["workout_type"],
                "sessions": row["sessions"],
                "distance_meters": row["total_distance"] or 0.0,
                "duration_seconds": row["total_duration"] or 0,
                "avg_pace_min_per_km": row["avg_pace"],
            }
            for row in rows
        ]

    async def training_log(self, athlete_id: str, year: int) -> list[dict]:
        year_start, year_end = self._year_range(year)

        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT id, start_time, workout_type, data
                FROM workouts
                WHERE athlete_id = ?
                  AND start_time >= ? AND start_time <= ?
                  AND workout_type IS NOT NULL
                ORDER BY start_time ASC
                """,
                (athlete_id, year_start, year_end),
            ).fetchall()

        return [
            {
                "id": row["id"],
                "date": row["start_time"][:10],
                "workout_type": row["workout_type"],
                "duration_seconds": json.loads(row["data"]).get("duration_seconds", 0),
                "distance_meters": json.loads(row["data"]).get("distance_meters") or 0,
                "name": json.loads(row["data"]).get("name", ""),
            }
            for row in rows
        ]

    async def daily_effort(self, athlete_id: str, since: date) -> list[dict]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    date(start_time) AS day,
                    SUM(
                        CASE
                            WHEN json_extract(data, '$.average_heartrate') IS NOT NULL
                            THEN (CAST(json_extract(data, '$.duration_seconds') AS REAL) / 3600.0)
                                 * ((json_extract(data, '$.average_heartrate') / 150.0)
                                    * (json_extract(data, '$.average_heartrate') / 150.0))
                                 * 100.0
                            ELSE CAST(json_extract(data, '$.duration_seconds') AS REAL) / 60.0
                        END
                    ) AS effort
                FROM workouts
                WHERE athlete_id = ? AND date(start_time) >= ?
                GROUP BY day
                ORDER BY day
                """,
                (athlete_id, since.isoformat()),
            ).fetchall()

        return [{"date": row["day"], "effort": row["effort"]} for row in rows]

    async def workouts_with_notes(self, athlete_id: str, year: int) -> list[dict]:
        year_start, year_end = self._year_range(year)

        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT id, start_time, workout_type, data
                FROM workouts
                WHERE athlete_id = ?
                  AND start_time >= ? AND start_time <= ?
                  AND json_extract(data, '$.private_note') IS NOT NULL
                  AND json_extract(data, '$.private_note') != ''
                ORDER BY start_time ASC
                """,
                (athlete_id, year_start, year_end),
            ).fetchall()

        results = []
        for row in rows:
            data = json.loads(row["data"])
            results.append({
                "id": row["id"],
                "date": row["start_time"][:10],
                "workout_type": row["workout_type"],
                "name": data.get("name", ""),
                "duration_seconds": data.get("duration_seconds", 0),
                "distance_meters": data.get("distance_meters") or 0,
                "average_heartrate": data.get("average_heartrate"),
                "private_note": data.get("private_note", ""),
            })
        return results
