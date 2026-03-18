"""PostgreSQL storage adapter for athletes, workouts, and weight entries."""

from datetime import date

from asyncpg import Pool

from forma.domain.athlete import Athlete
from forma.domain.weight_entry import WeightEntry
from forma.domain.workout import Workout
from forma.ports.athlete_repository import AthleteRepository
from forma.ports.weight_repository import WeightRepository
from forma.ports.workout_repository import WorkoutRepository


class PostgresStorage(AthleteRepository, WorkoutRepository, WeightRepository):
    """PostgreSQL-backed storage for all domain entities."""

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    # AthleteRepository

    async def get(self, athlete_id: str) -> Athlete | None:
        row = await self._pool.fetchrow(
            "SELECT data FROM athletes WHERE id = $1", athlete_id
        )
        if row:
            return Athlete.model_validate_json(row["data"])
        return None

    async def save(self, athlete: Athlete) -> None:
        await self._pool.execute(
            """
            INSERT INTO athletes (id, data, updated_at)
            VALUES ($1, $2, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
                data = EXCLUDED.data,
                updated_at = CURRENT_TIMESTAMP
            """,
            athlete.id,
            athlete.model_dump_json(),
        )

    async def delete(self, athlete_id: str) -> None:
        await self._pool.execute("DELETE FROM athletes WHERE id = $1", athlete_id)

    async def get_by_strava_id(self, strava_id: int) -> Athlete | None:
        row = await self._pool.fetchrow(
            "SELECT data FROM athletes WHERE (data::jsonb->>'strava_athlete_id')::bigint = $1",
            strava_id,
        )
        if row:
            return Athlete.model_validate_json(row["data"])
        return None

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
            workout.start_time.isoformat(),
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
            params.append(start_date.isoformat())
            clauses.append(f"start_time >= ${len(params)}")
        if end_date:
            params.append(end_date.isoformat())
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
            entry.recorded_at.isoformat(),
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
            recorded_at=date.fromisoformat(row["recorded_at"]),
            notes=row["notes"] or "",
        )
