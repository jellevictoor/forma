"""Tests for SQLiteStorage WeightRepository implementation."""

from datetime import date

import pytest

from fitness_coach.adapters.sqlite_storage import SQLiteStorage
from fitness_coach.domain.athlete import Athlete
from fitness_coach.domain.weight_entry import WeightEntry


def make_athlete(athlete_id: str = "athlete1") -> Athlete:
    return Athlete(id=athlete_id, name="Test Athlete")


def make_entry(
    entry_id: str = "e1",
    athlete_id: str = "athlete1",
    weight_kg: float = 75.0,
    recorded_at: date = date(2026, 2, 1),
    notes: str = "",
) -> WeightEntry:
    return WeightEntry(
        id=entry_id,
        athlete_id=athlete_id,
        weight_kg=weight_kg,
        recorded_at=recorded_at,
        notes=notes,
    )


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def storage(db_path):
    return SQLiteStorage(db_path)


@pytest.mark.asyncio
async def test_save_and_get_latest(storage):
    await storage.save(make_athlete())
    entry = make_entry()
    await storage.save_weight_entry(entry)

    result = await storage.get_latest_weight("athlete1")

    assert result.id == "e1"


@pytest.mark.asyncio
async def test_list_for_athlete_ordered_desc(storage):
    await storage.save(make_athlete())
    await storage.save_weight_entry(make_entry("e1", recorded_at=date(2026, 1, 1), weight_kg=74.0))
    await storage.save_weight_entry(make_entry("e2", recorded_at=date(2026, 2, 1), weight_kg=75.0))

    result = await storage.list_weight_entries("athlete1")

    assert result[0].id == "e2"


@pytest.mark.asyncio
async def test_delete_entry(storage):
    await storage.save(make_athlete())
    await storage.save_weight_entry(make_entry("e1"))
    await storage.delete_weight_entry("e1")

    result = await storage.list_weight_entries("athlete1")

    assert result == []


@pytest.mark.asyncio
async def test_list_limit(storage):
    await storage.save(make_athlete())
    for i in range(5):
        await storage.save_weight_entry(make_entry(f"e{i}", recorded_at=date(2026, 1, i + 1), weight_kg=70.0 + i))

    result = await storage.list_weight_entries("athlete1", limit=3)

    assert len(result) == 3
