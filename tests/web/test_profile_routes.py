"""Tests for profile routes."""

from datetime import date
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from forma.adapters.web.app import create_app
from forma.application.athlete_profile_service import AthleteProfileService
from forma.application.weight_tracking_service import WeightTrackingService
from forma.domain.athlete import Athlete
from forma.domain.weight_entry import WeightEntry


def make_athlete() -> Athlete:
    return Athlete(id="athlete1", name="Test Athlete")


def make_weight_entry() -> WeightEntry:
    return WeightEntry(id="e1", athlete_id="athlete1", weight_kg=75.0, recorded_at=date.today())


def make_mock_profile_service(athlete: Athlete | None = None) -> AthleteProfileService:
    svc = AsyncMock(spec=AthleteProfileService)
    svc.get_profile = AsyncMock(return_value=athlete or make_athlete())
    svc.update_profile = AsyncMock(return_value=make_athlete())
    svc.set_primary_goal = AsyncMock(return_value=make_athlete())
    svc.remove_primary_goal = AsyncMock(return_value=make_athlete())
    return svc


def make_mock_weight_service(entries: list | None = None) -> WeightTrackingService:
    svc = AsyncMock(spec=WeightTrackingService)
    svc.get_history = AsyncMock(return_value=entries or [])
    svc.chart_data = AsyncMock(return_value=[])
    svc.is_stale = AsyncMock(return_value=False)
    svc.record_weight = AsyncMock(return_value=make_weight_entry())
    svc.delete_entry = AsyncMock()
    return svc


@pytest.fixture
def client():
    app = create_app()

    async def override_profile_service():
        return make_mock_profile_service()

    async def override_weight_service():
        return make_mock_weight_service()

    from forma.adapters.web.dependencies import (
        get_athlete_id,
        get_athlete_profile_service,
        get_weight_tracking_service,
    )

    app.dependency_overrides[get_athlete_profile_service] = override_profile_service
    app.dependency_overrides[get_weight_tracking_service] = override_weight_service
    app.dependency_overrides[get_athlete_id] = lambda: "athlete1"
    return TestClient(app, follow_redirects=True)


def test_get_profile_renders(client):
    response = client.get("/profile")

    assert response.status_code == 200


def test_post_profile_updates(client):
    response = client.post(
        "/profile",
        data={"name": "New Name", "notes": ""},
    )

    assert response.status_code == 200


def test_post_weight_adds_entry(client):
    response = client.post("/profile/weight", data={"weight_kg": "76.5"})

    assert response.status_code == 200


def test_delete_weight_entry(client):
    response = client.delete("/profile/weight/e1")

    assert response.status_code == 200
