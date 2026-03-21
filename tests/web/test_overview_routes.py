"""Tests for overview routes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock


import pytest
from fastapi.testclient import TestClient

from forma.adapters.web.app import create_app
from forma.application.analytics_service import AnalyticsService, OverviewStats
from forma.application.athlete_profile_service import AthleteProfileService
from forma.application.sync_all_activities import FullStravaSync
from forma.domain.athlete import Athlete, SyncState
from forma.ports.workout_analytics_repository import SportSummary


def make_mock_analytics_service() -> AnalyticsService:
    service = AsyncMock(spec=AnalyticsService)
    service.overview_stats = AsyncMock(
        return_value=OverviewStats(year=2026,
            sport_summaries=[SportSummary("run", 10, 50000, 36000, None)],
            recent_workouts=[],
            weekly_volumes=[],
            personal_records=[],
        )
    )
    service.weekly_volume_chart_data = AsyncMock(return_value=[])
    service.training_log_data = AsyncMock(return_value=[])
    return service



def make_mock_workout_repo():
    repo = AsyncMock()
    repo.get_recent = AsyncMock(return_value=[])
    return repo


def make_mock_strava_sync(synced: int = 3) -> FullStravaSync:
    service = AsyncMock(spec=FullStravaSync)
    service.execute = AsyncMock(return_value=synced)
    service.resume_backfill = AsyncMock(return_value=0)
    return service


def make_mock_profile_service() -> AthleteProfileService:
    service = AsyncMock(spec=AthleteProfileService)
    service.get_profile = AsyncMock(return_value=Athlete(id="athlete1", name="Test"))
    return service


def _apply_overrides(app):
    from forma.adapters.web.dependencies import (
        get_analytics_service,
        get_athlete_id,
        get_athlete_profile_service,
        get_strava_sync,
        get_workout_repo,
    )
    app.dependency_overrides[get_analytics_service] = lambda: make_mock_analytics_service()
    app.dependency_overrides[get_workout_repo] = lambda: make_mock_workout_repo()
    app.dependency_overrides[get_strava_sync] = lambda: make_mock_strava_sync()
    app.dependency_overrides[get_athlete_profile_service] = lambda: make_mock_profile_service()
    app.dependency_overrides[get_athlete_id] = lambda: "athlete1"


@pytest.fixture
def client(tmp_path):
    app = create_app()
    _apply_overrides(app)
    return TestClient(app)


def test_overview_page_returns_200(client):
    response = client.get("/")

    assert response.status_code == 200


def test_overview_page_contains_html(client):
    response = client.get("/")

    assert "text/html" in response.headers["content-type"]


def test_weekly_volume_api_returns_json(client):
    response = client.get("/api/overview/weekly-volume")

    assert response.status_code == 200


def test_weekly_volume_api_content_type_is_json(client):
    response = client.get("/api/overview/weekly-volume")

    assert "application/json" in response.headers["content-type"]


def test_training_log_api_returns_200(client):
    response = client.get("/api/overview/training-log")

    assert response.status_code == 200


def test_training_log_api_returns_list(client):
    response = client.get("/api/overview/training-log")

    assert isinstance(response.json(), list)



def test_sync_status_returns_sync_state(client):
    response = client.get("/api/sync/status")

    assert response.json()["sync_state"] == "never_synced"


def test_sync_status_returns_null_cursor_by_default(client):
    response = client.get("/api/sync/status")

    assert response.json()["backfill_cursor"] is None


def test_sync_status_reflects_athlete_state():
    app = create_app()
    from forma.adapters.web.dependencies import (
        get_athlete_id,
        get_athlete_profile_service,
    )
    profile_service = AsyncMock(spec=AthleteProfileService)
    profile_service.get_profile = AsyncMock(
        return_value=Athlete(
            id="athlete1",
            name="Test",
            sync_state=SyncState.BACKFILL_PAUSED,
            backfill_cursor=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
    )
    app.dependency_overrides[get_athlete_profile_service] = lambda: profile_service
    app.dependency_overrides[get_athlete_id] = lambda: "athlete1"
    client = TestClient(app)

    response = client.get("/api/sync/status")

    assert response.json()["sync_state"] == "backfill_paused"


def test_resume_backfill_returns_started(client):
    response = client.post("/api/sync/resume-backfill")

    assert response.json()["status"] == "started"


