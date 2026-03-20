"""Tests for zone 2 compliance calculation in AnalyticsService."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from forma.application.analytics_service import AnalyticsService


@pytest.fixture
def analytics_repo():
    return AsyncMock()


@pytest.fixture
def workout_repo():
    return AsyncMock()


@pytest.fixture
def service(analytics_repo, workout_repo):
    return AnalyticsService(analytics_repo, workout_repo)


async def test_zone2_compliance_returns_zero_when_no_runs(service, analytics_repo):
    analytics_repo.runs_with_hr = AsyncMock(return_value=[])

    result = await service.zone2_compliance("a1", 185, None, date(2026, 3, 16), date(2026, 3, 22))

    assert result["zone2_pct"] == 0


async def test_zone2_compliance_counts_runs_in_zone(service, analytics_repo):
    analytics_repo.runs_with_hr = AsyncMock(return_value=[
        {"moving_time_seconds": 3600, "average_heartrate": 120},  # in Z2 (111-129.5)
        {"moving_time_seconds": 1800, "average_heartrate": 150},  # above Z2
    ])

    result = await service.zone2_compliance("a1", 185, None, date(2026, 3, 16), date(2026, 3, 22))

    assert result["zone2_pct"] == pytest.approx(66.7, abs=0.1)


async def test_zone2_compliance_uses_calibrated_zones(service, analytics_repo):
    # With VT1=150, Z2 = [135, 150)
    analytics_repo.runs_with_hr = AsyncMock(return_value=[
        {"moving_time_seconds": 3600, "average_heartrate": 140},  # in calibrated Z2
    ])

    result = await service.zone2_compliance("a1", 185, 150, date(2026, 3, 16), date(2026, 3, 22))

    assert result["zone2_pct"] == 100.0


async def test_zone2_compliance_returns_zone_bounds(service, analytics_repo):
    analytics_repo.runs_with_hr = AsyncMock(return_value=[])

    result = await service.zone2_compliance("a1", 185, None, date(2026, 3, 16), date(2026, 3, 22))

    assert result["zone2_lower"] == 111


async def test_zone2_compliance_returns_run_count(service, analytics_repo):
    analytics_repo.runs_with_hr = AsyncMock(return_value=[
        {"moving_time_seconds": 3600, "average_heartrate": 120},
        {"moving_time_seconds": 1800, "average_heartrate": 130},
    ])

    result = await service.zone2_compliance("a1", 185, None, date(2026, 3, 16), date(2026, 3, 22))

    assert result["run_count"] == 2
