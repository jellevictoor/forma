"""PostgreSQL storage adapter for athletes, workouts, and weight entries."""

import json
from datetime import date

from asyncpg import Pool

from forma.domain.athlete import (
    Athlete,
    Goal,
    GoalHistoryEntry,
    Injury,
    ScheduleTemplateSlot,
    SyncState,
)
from forma.domain.weight_entry import WeightEntry
from forma.domain.workout import Workout
from forma.ports.athlete_repository import AthleteRepository
from forma.ports.weight_repository import WeightRepository
from forma.ports.workout_repository import WorkoutRepository

_ATHLETE_COLUMNS = """
    id, name, date_of_birth, height_cm, weight_kg,
    max_hours_per_week, notes, max_heartrate, aerobic_threshold_bpm,
    role, is_blocked, ai_enabled, token_limit_30d,
    strava_athlete_id, strava_access_token, strava_refresh_token, strava_token_expires_at,
    goals, injuries, goal_history, schedule_template, equipment, preferred_workout_days,
    sync_state, backfill_cursor
"""


def _athlete_from_row(row) -> Athlete:
    return Athlete(
        id=row["id"],
        name=row["name"],
        date_of_birth=row["date_of_birth"],
        height_cm=row["height_cm"],
        weight_kg=row["weight_kg"],
        max_hours_per_week=row["max_hours_per_week"],
        notes=row["notes"] or "",
        max_heartrate=row["max_heartrate"],
        aerobic_threshold_bpm=row["aerobic_threshold_bpm"],
        role=row["role"],
        is_blocked=row["is_blocked"],
        ai_enabled=row["ai_enabled"],
        token_limit_30d=row["token_limit_30d"],
        strava_athlete_id=row["strava_athlete_id"],
        strava_access_token=row["strava_access_token"],
        strava_refresh_token=row["strava_refresh_token"],
        strava_token_expires_at=row["strava_token_expires_at"],
        goals=[Goal.model_validate(g) for g in json.loads(row["goals"])],
        injuries=[Injury.model_validate(i) for i in json.loads(row["injuries"])],
        goal_history=[GoalHistoryEntry.model_validate(g) for g in json.loads(row["goal_history"])],
        schedule_template=[ScheduleTemplateSlot.model_validate(s) for s in json.loads(row["schedule_template"])],
        equipment=json.loads(row["equipment"]),
        preferred_workout_days=json.loads(row["preferred_workout_days"]),
        sync_state=SyncState(row["sync_state"]),
        backfill_cursor=row["backfill_cursor"],
    )


class PostgresStorage(AthleteRepository, WorkoutRepository, WeightRepository):
    """PostgreSQL-backed storage for all domain entities."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    # AthleteRepository

    async def get(self, athlete_id: str) -> Athlete | None:
        row = await self._pool.fetchrow(
            f"SELECT {_ATHLETE_COLUMNS} FROM athletes WHERE id = $1", athlete_id
        )
        return _athlete_from_row(row) if row else None

    async def save(self, athlete: Athlete) -> None:
        await self._pool.execute(
            f"""
            INSERT INTO athletes ({_ATHLETE_COLUMNS}, updated_at)
            VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9,
                $10, $11, $12, $13,
                $14, $15, $16, $17,
                $18, $19, $20, $21, $22, $23,
                $24, $25,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (id) DO UPDATE SET
                name                   = EXCLUDED.name,
                date_of_birth          = EXCLUDED.date_of_birth,
                height_cm              = EXCLUDED.height_cm,
                weight_kg              = EXCLUDED.weight_kg,
                max_hours_per_week     = EXCLUDED.max_hours_per_week,
                notes                  = EXCLUDED.notes,
                max_heartrate          = EXCLUDED.max_heartrate,
                aerobic_threshold_bpm  = EXCLUDED.aerobic_threshold_bpm,
                role                   = EXCLUDED.role,
                is_blocked             = EXCLUDED.is_blocked,
                ai_enabled             = EXCLUDED.ai_enabled,
                token_limit_30d        = EXCLUDED.token_limit_30d,
                strava_athlete_id      = EXCLUDED.strava_athlete_id,
                strava_access_token    = EXCLUDED.strava_access_token,
                strava_refresh_token   = EXCLUDED.strava_refresh_token,
                strava_token_expires_at = EXCLUDED.strava_token_expires_at,
                goals                  = EXCLUDED.goals,
                injuries               = EXCLUDED.injuries,
                goal_history           = EXCLUDED.goal_history,
                schedule_template      = EXCLUDED.schedule_template,
                equipment              = EXCLUDED.equipment,
                preferred_workout_days = EXCLUDED.preferred_workout_days,
                sync_state             = EXCLUDED.sync_state,
                backfill_cursor        = EXCLUDED.backfill_cursor,
                updated_at             = CURRENT_TIMESTAMP
            """,
            athlete.id,
            athlete.name,
            athlete.date_of_birth,
            athlete.height_cm,
            athlete.weight_kg,
            athlete.max_hours_per_week,
            athlete.notes,
            athlete.max_heartrate,
            athlete.aerobic_threshold_bpm,
            athlete.role.value,
            athlete.is_blocked,
            athlete.ai_enabled,
            athlete.token_limit_30d,
            athlete.strava_athlete_id,
            athlete.strava_access_token,
            athlete.strava_refresh_token,
            athlete.strava_token_expires_at,
            json.dumps([g.model_dump(mode="json") for g in athlete.goals]),
            json.dumps([i.model_dump(mode="json") for i in athlete.injuries]),
            json.dumps([g.model_dump(mode="json") for g in athlete.goal_history]),
            json.dumps([s.model_dump(mode="json") for s in athlete.schedule_template]),
            json.dumps(athlete.equipment),
            json.dumps(athlete.preferred_workout_days),
            athlete.sync_state.value,
            athlete.backfill_cursor,
        )

    async def delete(self, athlete_id: str) -> None:
        await self._pool.execute("DELETE FROM athletes WHERE id = $1", athlete_id)

    async def get_by_strava_id(self, strava_id: int) -> Athlete | None:
        row = await self._pool.fetchrow(
            f"SELECT {_ATHLETE_COLUMNS} FROM athletes WHERE strava_athlete_id = $1",
            strava_id,
        )
        return _athlete_from_row(row) if row else None

    # WorkoutRepository

    async def get_workout(self, workout_id: str) -> Workout | None:
        row = await self._pool.fetchrow(
            "SELECT data FROM workouts WHERE id = $1", workout_id
        )
        if row:
            return Workout.model_validate_json(row["data"])
        return None

    async def get_workout_by_strava_id(self, strava_id: int) -> Workout | None:
        row = await self._pool.fetchrow(
            "SELECT data FROM workouts WHERE strava_id = $1", strava_id
        )
        if row:
            return Workout.model_validate_json(row["data"])
        return None

    async def save_workout(self, workout: Workout) -> None:
        await self._pool.execute(
            """
            INSERT INTO workouts (
                id, athlete_id, strava_id, start_time, workout_type,
                distance_meters, duration_seconds, moving_time_seconds, average_heartrate,
                data
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (id) DO UPDATE SET
                data                = EXCLUDED.data,
                workout_type        = EXCLUDED.workout_type,
                distance_meters     = EXCLUDED.distance_meters,
                duration_seconds    = EXCLUDED.duration_seconds,
                moving_time_seconds = EXCLUDED.moving_time_seconds,
                average_heartrate   = EXCLUDED.average_heartrate
            """,
            workout.id,
            workout.athlete_id,
            workout.strava_id,
            workout.start_time,
            workout.workout_type.value,
            workout.distance_meters,
            workout.duration_seconds,
            workout.moving_time_seconds,
            workout.average_heartrate,
            workout.model_dump_json(),
        )

    async def delete_workout(self, workout_id: str) -> None:
        await self._pool.execute("DELETE FROM workouts WHERE id = $1", workout_id)

    async def list_workouts_for_athlete(
        self,
        athlete_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> list[Workout]:
        params: list = [athlete_id]
        clauses = ["athlete_id = $1"]

        if start_date:
            params.append(start_date)
            clauses.append(f"start_time >= ${len(params)}")
        if end_date:
            params.append(end_date)
            clauses.append(f"start_time <= ${len(params)}")

        params.append(limit)
        query = (
            f"SELECT data FROM workouts WHERE {' AND '.join(clauses)}"
            f" ORDER BY start_time DESC LIMIT ${len(params)}"
        )
        rows = await self._pool.fetch(query, *params)
        return [Workout.model_validate_json(row["data"]) for row in rows]

    async def get_recent(self, athlete_id: str, count: int = 10) -> list[Workout]:
        return await self.list_workouts_for_athlete(athlete_id, limit=count)

    async def get_oldest(self, athlete_id: str) -> Workout | None:
        row = await self._pool.fetchrow(
            "SELECT data FROM workouts WHERE athlete_id = $1 ORDER BY start_time ASC LIMIT 1",
            athlete_id,
        )
        if not row:
            return None
        return Workout.model_validate_json(row["data"])

    # WeightRepository

    async def save_weight_entry(self, entry: WeightEntry) -> None:
        await self._pool.execute(
            """
            INSERT INTO weight_entries (id, athlete_id, weight_kg, recorded_at, notes)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (id) DO UPDATE SET
                weight_kg = EXCLUDED.weight_kg,
                recorded_at = EXCLUDED.recorded_at,
                notes = EXCLUDED.notes
            """,
            entry.id,
            entry.athlete_id,
            entry.weight_kg,
            entry.recorded_at,
            entry.notes,
        )

    async def list_weight_entries(self, athlete_id: str, limit: int = 90) -> list[WeightEntry]:
        rows = await self._pool.fetch(
            """
            SELECT id, athlete_id, weight_kg, recorded_at, notes
            FROM weight_entries
            WHERE athlete_id = $1
            ORDER BY recorded_at DESC
            LIMIT $2
            """,
            athlete_id,
            limit,
        )
        return [self._row_to_weight_entry(row) for row in rows]

    async def get_latest_weight(self, athlete_id: str) -> WeightEntry | None:
        row = await self._pool.fetchrow(
            """
            SELECT id, athlete_id, weight_kg, recorded_at, notes
            FROM weight_entries
            WHERE athlete_id = $1
            ORDER BY recorded_at DESC
            LIMIT 1
            """,
            athlete_id,
        )
        if row:
            return self._row_to_weight_entry(row)
        return None

    async def delete_weight_entry(self, entry_id: str) -> None:
        await self._pool.execute("DELETE FROM weight_entries WHERE id = $1", entry_id)

    def _row_to_weight_entry(self, row) -> WeightEntry:
        return WeightEntry(
            id=row["id"],
            athlete_id=row["athlete_id"],
            weight_kg=row["weight_kg"],
            recorded_at=row["recorded_at"],
            notes=row["notes"] or "",
        )
