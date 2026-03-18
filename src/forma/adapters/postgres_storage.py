"""PostgreSQL storage adapter for athletes, workouts, and weight entries."""

import json
from datetime import date

from asyncpg import Pool

from forma.domain.athlete import Athlete
from forma.domain.weight_entry import WeightEntry
from forma.domain.workout import Workout
from forma.ports.athlete_repository import AthleteRepository
from forma.ports.weight_repository import WeightRepository
from forma.ports.workout_repository import WorkoutRepository

# Fields stored as proper columns — excluded from the JSON profile blob.
_ATHLETE_COLUMN_FIELDS = frozenset({
    "role", "is_blocked", "ai_enabled", "token_limit_30d",
    "strava_athlete_id", "strava_access_token", "strava_refresh_token", "strava_token_expires_at",
})

_ATHLETE_SELECT = """
    id, data, role, is_blocked, ai_enabled, token_limit_30d,
    strava_athlete_id, strava_access_token, strava_refresh_token, strava_token_expires_at
"""


def _athlete_from_row(row) -> Athlete:
    """Reconstruct an Athlete by merging the profile blob with the column fields."""
    data = json.loads(row["data"])
    data.update({
        "role": row["role"],
        "is_blocked": row["is_blocked"],
        "ai_enabled": row["ai_enabled"],
        "token_limit_30d": row["token_limit_30d"],
        "strava_athlete_id": row["strava_athlete_id"],
        "strava_access_token": row["strava_access_token"],
        "strava_refresh_token": row["strava_refresh_token"],
        "strava_token_expires_at": row["strava_token_expires_at"],
    })
    return Athlete.model_validate(data)


class PostgresStorage(AthleteRepository, WorkoutRepository, WeightRepository):
    """PostgreSQL-backed storage for all domain entities."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    # AthleteRepository

    async def get(self, athlete_id: str) -> Athlete | None:
        row = await self._pool.fetchrow(
            f"SELECT {_ATHLETE_SELECT} FROM athletes WHERE id = $1", athlete_id
        )
        return _athlete_from_row(row) if row else None

    async def save(self, athlete: Athlete) -> None:
        profile_json = athlete.model_dump_json(exclude=_ATHLETE_COLUMN_FIELDS)
        await self._pool.execute(
            """
            INSERT INTO athletes (
                id, data,
                role, is_blocked, ai_enabled, token_limit_30d,
                strava_athlete_id, strava_access_token, strava_refresh_token,
                strava_token_expires_at,
                updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
                data                    = EXCLUDED.data,
                role                    = EXCLUDED.role,
                is_blocked              = EXCLUDED.is_blocked,
                ai_enabled              = EXCLUDED.ai_enabled,
                token_limit_30d         = EXCLUDED.token_limit_30d,
                strava_athlete_id       = EXCLUDED.strava_athlete_id,
                strava_access_token     = EXCLUDED.strava_access_token,
                strava_refresh_token    = EXCLUDED.strava_refresh_token,
                strava_token_expires_at = EXCLUDED.strava_token_expires_at,
                updated_at              = CURRENT_TIMESTAMP
            """,
            athlete.id,
            profile_json,
            athlete.role.value,
            athlete.is_blocked,
            athlete.ai_enabled,
            athlete.token_limit_30d,
            athlete.strava_athlete_id,
            athlete.strava_access_token,
            athlete.strava_refresh_token,
            athlete.strava_token_expires_at,
        )

    async def delete(self, athlete_id: str) -> None:
        await self._pool.execute("DELETE FROM athletes WHERE id = $1", athlete_id)

    async def get_by_strava_id(self, strava_id: int) -> Athlete | None:
        row = await self._pool.fetchrow(
            f"SELECT {_ATHLETE_SELECT} FROM athletes WHERE strava_athlete_id = $1",
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
            INSERT INTO workouts (id, athlete_id, strava_id, start_time, workout_type, data)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (id) DO UPDATE SET
                data = EXCLUDED.data,
                workout_type = EXCLUDED.workout_type
            """,
            workout.id,
            workout.athlete_id,
            workout.strava_id,
            workout.start_time,
            workout.workout_type.value,
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
