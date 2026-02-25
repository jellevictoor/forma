"""Tests for WeightTrackingService."""

from datetime import date, timedelta
from unittest.mock import AsyncMock


from fitness_coach.application.weight_tracking_service import WeightTrackingService
from fitness_coach.domain.weight_entry import WeightEntry


def make_entry(
    entry_id: str = "e1",
    athlete_id: str = "athlete1",
    weight_kg: float = 75.0,
    recorded_at: date | None = None,
) -> WeightEntry:
    return WeightEntry(
        id=entry_id,
        athlete_id=athlete_id,
        weight_kg=weight_kg,
        recorded_at=recorded_at or date.today(),
    )


def make_service(latest: WeightEntry | None = None, entries: list | None = None) -> WeightTrackingService:
    weight_repo = AsyncMock()
    weight_repo.save_weight_entry = AsyncMock()
    weight_repo.get_latest_weight = AsyncMock(return_value=latest)
    weight_repo.list_weight_entries = AsyncMock(return_value=entries or [])
    weight_repo.delete_weight_entry = AsyncMock()
    return WeightTrackingService(weight_repo)


async def test_record_weight_saved():
    service = make_service()

    entry = await service.record_weight("athlete1", 75.5)

    assert entry.weight_kg == 75.5


async def test_is_stale_no_entries():
    service = make_service(latest=None)

    result = await service.is_stale("athlete1")

    assert result is True


async def test_is_stale_recent_entry():
    entry = make_entry(recorded_at=date.today())
    service = make_service(latest=entry)

    result = await service.is_stale("athlete1")

    assert result is False


async def test_is_stale_old_entry():
    old_date = date.today() - timedelta(days=8)
    entry = make_entry(recorded_at=old_date)
    service = make_service(latest=entry)

    result = await service.is_stale("athlete1")

    assert result is True


async def test_chart_data_format():
    entries = [
        make_entry("e2", recorded_at=date(2026, 2, 10), weight_kg=76.0),
        make_entry("e1", recorded_at=date(2026, 2, 1), weight_kg=75.0),
    ]
    service = make_service(entries=entries)

    result = await service.chart_data("athlete1")

    assert result[0] == {"date": "2026-02-01", "weight_kg": 75.0}
