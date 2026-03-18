"""Tests for SQLiteStreamRepository adapter."""

import pytest

from forma.adapters.sqlite_stream_repository import SQLiteStreamRepository
from forma.ports.stream_repository import WorkoutStreams


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def repo(db_path):
    return SQLiteStreamRepository(db_path)


def _sample_streams(**overrides) -> WorkoutStreams:
    defaults = dict(
        latlng=[[52.37, 4.89], [52.371, 4.891], [52.372, 4.892]],
        time=[0, 5, 10],
        velocity_smooth=[3.0, 3.2, 3.1],
        heartrate=[140, 145, 142],
    )
    defaults.update(overrides)
    return WorkoutStreams(**defaults)


async def test_get_returns_none_for_unknown(repo):
    result = await repo.get("unknown-workout")

    assert result is None


async def test_get_returns_streams_after_save(repo):
    await repo.save("w1", _sample_streams())

    result = await repo.get("w1")

    assert result is not None


async def test_saved_latlng_is_preserved(repo):
    latlng = [[52.37, 4.89], [52.371, 4.891]]
    await repo.save("w1", _sample_streams(latlng=latlng))

    result = await repo.get("w1")

    assert result.latlng == latlng


async def test_saved_velocity_smooth_is_preserved(repo):
    await repo.save("w1", _sample_streams(velocity_smooth=[2.5, 3.0, 3.5]))

    result = await repo.get("w1")

    assert result.velocity_smooth == [2.5, 3.0, 3.5]


async def test_saved_heartrate_is_preserved(repo):
    await repo.save("w1", _sample_streams(heartrate=[130, 135, 140]))

    result = await repo.get("w1")

    assert result.heartrate == [130, 135, 140]


async def test_heartrate_can_be_none(repo):
    await repo.save("w1", _sample_streams(heartrate=None))

    result = await repo.get("w1")

    assert result.heartrate is None


async def test_save_overwrites_existing(repo):
    await repo.save("w1", _sample_streams(velocity_smooth=[1.0, 2.0]))
    await repo.save("w1", _sample_streams(velocity_smooth=[3.0, 4.0]))

    result = await repo.get("w1")

    assert result.velocity_smooth == [3.0, 4.0]


async def test_workouts_are_isolated(repo):
    await repo.save("w1", _sample_streams(velocity_smooth=[1.0]))
    await repo.save("w2", _sample_streams(velocity_smooth=[2.0]))

    result = await repo.get("w1")

    assert result.velocity_smooth == [1.0]
