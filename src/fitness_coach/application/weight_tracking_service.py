"""Weight tracking service."""

import uuid
from datetime import date, timedelta

from fitness_coach.domain.weight_entry import WeightEntry
from fitness_coach.ports.weight_repository import WeightRepository

STALE_DAYS = 7


class WeightTrackingService:
    """Manages athlete weight entries and provides chart data."""

    def __init__(self, weight_repo: WeightRepository) -> None:
        self._weights = weight_repo

    async def record_weight(
        self, athlete_id: str, weight_kg: float, notes: str = ""
    ) -> WeightEntry:
        entry = WeightEntry(
            id=str(uuid.uuid4()),
            athlete_id=athlete_id,
            weight_kg=weight_kg,
            recorded_at=date.today(),
            notes=notes,
        )
        await self._weights.save_weight_entry(entry)
        return entry

    async def get_history(self, athlete_id: str, limit: int = 90) -> list[WeightEntry]:
        return await self._weights.list_weight_entries(athlete_id, limit=limit)

    async def get_latest(self, athlete_id: str) -> WeightEntry | None:
        return await self._weights.get_latest_weight(athlete_id)

    async def delete_entry(self, entry_id: str) -> None:
        await self._weights.delete_weight_entry(entry_id)

    async def is_stale(self, athlete_id: str) -> bool:
        latest = await self._weights.get_latest_weight(athlete_id)
        if latest is None:
            return True
        return (date.today() - latest.recorded_at) > timedelta(days=STALE_DAYS)

    async def chart_data(self, athlete_id: str) -> list[dict]:
        entries = await self._weights.list_weight_entries(athlete_id, limit=90)
        return [
            {"date": e.recorded_at.isoformat(), "weight_kg": e.weight_kg}
            for e in reversed(entries)
        ]
