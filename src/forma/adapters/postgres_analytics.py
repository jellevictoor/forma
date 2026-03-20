"""PostgreSQL read-side adapter for workout analytics queries."""

from datetime import date

from asyncpg import Pool

from forma.domain.workout import Workout
from forma.ports.workout_analytics_repository import (
    PersonalRecord,
    SportSummary,
    WeeklyVolume,
    WorkoutAnalyticsRepository,
)

_WEEK_START = "date_trunc('week', start_time::timestamp)::date"
_DISTANCE = "distance_meters"
_DURATION = "duration_seconds"
_MOVING_TIME = "moving_time_seconds"
_HEARTRATE = "average_heartrate"


class PostgresAnalyticsRepository(WorkoutAnalyticsRepository):
    """PostgreSQL analytics queries over the workouts table."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    def _year_range(self, year: int) -> tuple[date, date]:
        return date(year, 1, 1), date(year, 12, 31)

    async def weekly_volume(
        self,
        athlete_id: str,
        workout_type: str | None,
        year: int,
    ) -> list[WeeklyVolume]:
        year_start, year_end = self._year_range(year)
        params: list = [athlete_id, year_start, year_end]
        clauses = ["athlete_id = $1", "start_time >= $2", "start_time <= $3"]

        if workout_type:
            params.append(workout_type)
            clauses.append(f"workout_type = ${len(params)}")

        where = " AND ".join(clauses)
        rows = await self._pool.fetch(
            f"""
            SELECT
                {_WEEK_START} AS week_start,
                workout_type,
                SUM({_DISTANCE}) AS total_distance,
                SUM({_DURATION}) AS total_duration,
                COUNT(*) AS workout_count
            FROM workouts
            WHERE {where}
            GROUP BY week_start, workout_type
            ORDER BY week_start
            """,
            *params,
        )
        return [
            WeeklyVolume(
                week_start=row["week_start"],
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
        rows = await self._pool.fetch(
            f"""
            SELECT
                {_WEEK_START} AS week_start,
                workout_type,
                SUM({_DISTANCE}) AS total_distance,
                SUM({_DURATION}) AS total_duration,
                COUNT(*) AS workout_count
            FROM workouts
            WHERE athlete_id = $1 AND start_time >= $2 AND start_time <= $3
            GROUP BY week_start, workout_type
            ORDER BY week_start
            """,
            athlete_id,
            since,
            until,
        )
        return [
            WeeklyVolume(
                week_start=row["week_start"],
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
        rows = await self._pool.fetch(
            f"""
            SELECT id, start_time, data
            FROM workouts
            WHERE athlete_id = $1 AND workout_type = 'run'
              AND {_DISTANCE} IS NOT NULL
              AND {_MOVING_TIME} IS NOT NULL
            ORDER BY start_time
            """,
            athlete_id,
        )
        workouts = [
            (row["id"], row["start_time"].date(), Workout.model_validate_json(row["data"]))
            for row in rows
        ]
        return [
            record
            for bucket in distances_meters
            if (record := self._best_effort_for_distance(workouts, bucket)) is not None
        ]

    def _best_effort_for_distance(
        self,
        workouts: list[tuple[str, date, Workout]],
        min_distance: float,
    ) -> PersonalRecord | None:
        candidates = [
            (wid, achieved_on, w)
            for wid, achieved_on, w in workouts
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
        rows = await self._pool.fetch(
            f"""
            SELECT
                {_WEEK_START} AS week_start,
                AVG(
                    {_MOVING_TIME} / 60.0
                    / ({_DISTANCE} / 1000.0)
                ) AS pace_min_per_km
            FROM workouts
            WHERE athlete_id = $1 AND workout_type = $2
              AND start_time >= $3 AND start_time <= $4
              AND {_DISTANCE} > 0
              AND {_MOVING_TIME} > 0
            GROUP BY week_start
            ORDER BY week_start
            """,
            athlete_id,
            workout_type,
            year_start,
            year_end,
        )
        return [
            {"week_start": str(row["week_start"]), "pace_min_per_km": row["pace_min_per_km"]}
            for row in rows
        ]

    async def pace_trend_for_range(
        self,
        athlete_id: str,
        workout_type: str,
        since: date,
        until: date,
    ) -> list[dict]:
        rows = await self._pool.fetch(
            f"""
            SELECT
                {_WEEK_START} AS week_start,
                AVG(
                    {_MOVING_TIME} / 60.0
                    / ({_DISTANCE} / 1000.0)
                ) AS pace_min_per_km
            FROM workouts
            WHERE athlete_id = $1 AND workout_type = $2
              AND start_time >= $3 AND start_time <= $4
              AND {_DISTANCE} > 0
              AND {_MOVING_TIME} > 0
            GROUP BY week_start
            ORDER BY week_start
            """,
            athlete_id,
            workout_type,
            since,
            until,
        )
        return [
            {"week_start": str(row["week_start"]), "pace_min_per_km": row["pace_min_per_km"]}
            for row in rows
        ]

    async def sport_summaries(self, athlete_id: str, year: int) -> list[SportSummary]:
        year_start, year_end = self._year_range(year)
        rows = await self._pool.fetch(
            f"""
            SELECT
                workout_type,
                COUNT(*) AS total_workouts,
                SUM({_DISTANCE}) AS total_distance,
                SUM({_DURATION}) AS total_duration,
                MAX(start_time::date) AS most_recent
            FROM workouts
            WHERE athlete_id = $1 AND workout_type IS NOT NULL
              AND start_time >= $2 AND start_time <= $3
            GROUP BY workout_type
            ORDER BY total_workouts DESC
            """,
            athlete_id,
            year_start,
            year_end,
        )
        return [
            SportSummary(
                workout_type=row["workout_type"],
                total_workouts=row["total_workouts"],
                total_distance_meters=row["total_distance"] or 0.0,
                total_duration_seconds=row["total_duration"] or 0,
                most_recent=row["most_recent"],
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

        params: list = [athlete_id]
        clauses = ["athlete_id = $1"]

        if date_from:
            params.append(date_from)
            clauses.append(f"start_time >= ${len(params)}")
        if date_to:
            params.append(date_to)
            clauses.append(f"start_time <= ${len(params)}")
        if workout_type and workout_type != "all":
            params.append(workout_type)
            clauses.append(f"workout_type = ${len(params)}")

        where = " AND ".join(clauses)
        total = await self._pool.fetchval(
            f"SELECT COUNT(*) FROM workouts WHERE {where}", *params
        )

        params.extend([page_size, offset])
        rows = await self._pool.fetch(
            f"SELECT data FROM workouts WHERE {where} ORDER BY start_time DESC"
            f" LIMIT ${len(params) - 1} OFFSET ${len(params)}",
            *params,
        )
        workouts = [Workout.model_validate_json(row["data"]) for row in rows]
        return workouts, total

    async def strength_frequency(self, athlete_id: str, year: int) -> list[dict]:
        year_start, year_end = self._year_range(year)
        rows = await self._pool.fetch(
            f"""
            SELECT
                {_WEEK_START} AS week_start,
                COUNT(*) AS count
            FROM workouts
            WHERE athlete_id = $1 AND workout_type = 'strength'
              AND start_time >= $2 AND start_time <= $3
            GROUP BY week_start
            ORDER BY week_start
            """,
            athlete_id,
            year_start,
            year_end,
        )
        return [{"week_start": str(row["week_start"]), "count": row["count"]} for row in rows]

    async def climbing_sessions(self, athlete_id: str, year: int) -> list[dict]:
        year_start, year_end = self._year_range(year)
        rows = await self._pool.fetch(
            """
            SELECT id, start_time, duration_seconds, data::jsonb->>'name' AS name
            FROM workouts
            WHERE athlete_id = $1 AND workout_type = 'climbing'
              AND start_time >= $2 AND start_time <= $3
            ORDER BY start_time DESC
            """,
            athlete_id,
            year_start,
            year_end,
        )
        return [
            {
                "id": row["id"],
                "date": str(row["start_time"].date()),
                "duration_seconds": row["duration_seconds"] or 0,
                "name": row["name"] or "",
            }
            for row in rows
        ]

    async def sport_stats_for_month(self, athlete_id: str, year: int, month: int) -> list[dict]:
        start = date(year, month, 1)
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1
        end = date(next_year, next_month, 1)

        rows = await self._pool.fetch(
            f"""
            SELECT
                workout_type,
                COUNT(*) AS sessions,
                SUM({_DISTANCE}) AS total_distance,
                SUM({_DURATION}) AS total_duration,
                AVG(
                    CASE WHEN {_DISTANCE} > 0 AND {_MOVING_TIME} > 0
                         THEN {_MOVING_TIME} / 60.0 / ({_DISTANCE} / 1000.0)
                    END
                ) AS avg_pace
            FROM workouts
            WHERE athlete_id = $1
              AND start_time >= $2 AND start_time < $3
              AND workout_type IS NOT NULL
            GROUP BY workout_type
            ORDER BY workout_type
            """,
            athlete_id,
            start,
            end,
        )
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
        rows = await self._pool.fetch(
            """
            SELECT id, start_time, workout_type,
                   duration_seconds, distance_meters,
                   data::jsonb->>'name' AS name
            FROM workouts
            WHERE athlete_id = $1
              AND start_time >= $2 AND start_time <= $3
              AND workout_type IS NOT NULL
            ORDER BY start_time ASC
            """,
            athlete_id,
            year_start,
            year_end,
        )
        return [
            {
                "id": row["id"],
                "date": str(row["start_time"].date()),
                "workout_type": row["workout_type"],
                "duration_seconds": row["duration_seconds"] or 0,
                "distance_meters": row["distance_meters"] or 0,
                "name": row["name"] or "",
            }
            for row in rows
        ]

    async def daily_effort(self, athlete_id: str, since: date) -> list[dict]:
        _duration_hours = f"({_DURATION})::float / 3600.0"
        rows = await self._pool.fetch(
            f"""
            SELECT
                start_time::date AS day,
                SUM(
                    CASE
                        WHEN {_HEARTRATE} IS NOT NULL
                        THEN ({_duration_hours})
                             * (({_HEARTRATE} / 150.0) * ({_HEARTRATE} / 150.0))
                             * 100.0
                        ELSE ({_DURATION})::float / 60.0
                    END
                ) AS effort
            FROM workouts
            WHERE athlete_id = $1 AND start_time >= $2
            GROUP BY day
            ORDER BY day
            """,
            athlete_id,
            since,
        )
        return [{"date": str(row["day"]), "effort": row["effort"]} for row in rows]

    async def runs_with_hr(
        self,
        athlete_id: str,
        since: date,
        until: date,
    ) -> list[dict]:
        rows = await self._pool.fetch(
            f"""
            SELECT {_MOVING_TIME} AS moving_time_seconds,
                   {_HEARTRATE} AS average_heartrate
            FROM workouts
            WHERE athlete_id = $1
              AND workout_type = 'run'
              AND start_time >= $2
              AND start_time <= $3
              AND {_HEARTRATE} IS NOT NULL
              AND {_MOVING_TIME} IS NOT NULL
            """,
            athlete_id,
            since,
            until,
        )
        return [
            {"moving_time_seconds": row["moving_time_seconds"], "average_heartrate": row["average_heartrate"]}
            for row in rows
        ]

    async def recent_same_type_summary(
        self,
        athlete_id: str,
        workout_type: str,
        exclude_id: str,
        count: int = 4,
    ) -> list[dict]:
        rows = await self._pool.fetch(
            f"""
            SELECT
                start_time::date AS day,
                {_DURATION} / 60.0 AS duration_minutes,
                {_HEARTRATE} AS avg_hr
            FROM workouts
            WHERE athlete_id = $1
              AND workout_type = $2
              AND id != $3
            ORDER BY start_time DESC
            LIMIT $4
            """,
            athlete_id,
            workout_type,
            exclude_id,
            count,
        )
        return [
            {
                "date": str(row["day"]),
                "duration_minutes": round(row["duration_minutes"] or 0, 1),
                "avg_hr": round(row["avg_hr"]) if row["avg_hr"] else None,
            }
            for row in rows
        ]

    async def distinct_sport_types(self, athlete_id: str) -> list[str]:
        rows = await self._pool.fetch(
            """
            SELECT workout_type
            FROM workouts
            WHERE athlete_id = $1 AND workout_type IS NOT NULL
            GROUP BY workout_type
            ORDER BY COUNT(*) DESC
            """,
            athlete_id,
        )
        return [row["workout_type"] for row in rows]

    async def workouts_with_notes(self, athlete_id: str, year: int) -> list[dict]:
        year_start, year_end = self._year_range(year)
        rows = await self._pool.fetch(
            """
            SELECT id, start_time, workout_type,
                   duration_seconds, distance_meters, average_heartrate,
                   data::jsonb->>'name'         AS name,
                   data::jsonb->>'private_note' AS private_note
            FROM workouts
            WHERE athlete_id = $1
              AND start_time >= $2 AND start_time <= $3
              AND (data::jsonb->>'private_note') IS NOT NULL
              AND (data::jsonb->>'private_note') != ''
            ORDER BY start_time ASC
            """,
            athlete_id,
            year_start,
            year_end,
        )
        return [
            {
                "id": row["id"],
                "date": str(row["start_time"].date()),
                "workout_type": row["workout_type"],
                "name": row["name"] or "",
                "duration_seconds": row["duration_seconds"] or 0,
                "distance_meters": row["distance_meters"] or 0,
                "average_heartrate": row["average_heartrate"],
                "private_note": row["private_note"] or "",
            }
            for row in rows
        ]
