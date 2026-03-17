"""Tests for overview routes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from forma.adapters.web.app import create_app
from forma.application.analytics_service import AnalyticsService, OverviewStats
from forma.application.sync_all_activities import FullStravaSync
from forma.application.weekly_recap import WeeklyRecapService
from forma.ports.recap_cache_repository import CachedRecap
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


def make_cached_recap() -> CachedRecap:
    return CachedRecap(
        summary="Solid week.",
        highlight="New PR.",
        form_note="Fresh.",
        focus=["Add tempo run"],
        generated_at=datetime.now(tz=timezone.utc),
        latest_activity_at=None,
    )


def make_mock_recap_service(cached: CachedRecap | None = None) -> WeeklyRecapService:
    service = AsyncMock(spec=WeeklyRecapService)
    service.get_cached = AsyncMock(return_value=cached)
    service.generate_and_cache = AsyncMock(return_value=make_cached_recap())
    return service


def make_mock_workout_repo():
    repo = AsyncMock()
    repo.get_recent = AsyncMock(return_value=[])
    return repo


def make_mock_strava_sync(synced: int = 3) -> FullStravaSync:
    service = AsyncMock(spec=FullStravaSync)
    service.execute = AsyncMock(return_value=synced)
    return service


@pytest.fixture
def client(tmp_path):
    app = create_app()

    async def override_analytics_service():
        return make_mock_analytics_service()

    async def override_recap_service():
        return make_mock_recap_service(cached=make_cached_recap())

    async def override_workout_repo():
        return make_mock_workout_repo()

    async def override_strava_sync():
        return make_mock_strava_sync()

    from forma.adapters.web.dependencies import (
        get_analytics_service,
        get_athlete_id,
        get_strava_sync,
        get_weekly_recap_service,
        get_workout_repo,
    )
    app.dependency_overrides[get_analytics_service] = override_analytics_service
    app.dependency_overrides[get_weekly_recap_service] = override_recap_service
    app.dependency_overrides[get_workout_repo] = override_workout_repo
    app.dependency_overrides[get_strava_sync] = override_strava_sync
    app.dependency_overrides[get_athlete_id] = lambda: "athlete1"

    return TestClient(app)


@pytest.fixture
def client_no_cache(tmp_path):
    app = create_app()

    async def override_analytics_service():
        return make_mock_analytics_service()

    async def override_recap_service():
        return make_mock_recap_service(cached=None)

    async def override_workout_repo():
        return make_mock_workout_repo()

    async def override_strava_sync():
        return make_mock_strava_sync()

    from forma.adapters.web.dependencies import (
        get_analytics_service,
        get_athlete_id,
        get_strava_sync,
        get_weekly_recap_service,
        get_workout_repo,
    )
    app.dependency_overrides[get_analytics_service] = override_analytics_service
    app.dependency_overrides[get_weekly_recap_service] = override_recap_service
    app.dependency_overrides[get_workout_repo] = override_workout_repo
    app.dependency_overrides[get_strava_sync] = override_strava_sync
    app.dependency_overrides[get_athlete_id] = lambda: "athlete1"

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


def test_weekly_recap_api_returns_200_when_cached(client):
    response = client.get("/api/overview/weekly-recap")

    assert response.status_code == 200


def test_weekly_recap_api_returns_cached_true_when_recap_exists(client):
    response = client.get("/api/overview/weekly-recap")

    assert response.json()["cached"] is True


def test_weekly_recap_api_returns_cached_false_when_no_recap(client_no_cache):
    response = client_no_cache.get("/api/overview/weekly-recap")

    assert response.json()["cached"] is False


def test_weekly_recap_api_returns_summary_when_cached(client):
    response = client.get("/api/overview/weekly-recap")

    assert "summary" in response.json()


def test_weekly_recap_api_returns_focus_list_when_cached(client):
    response = client.get("/api/overview/weekly-recap")

    assert isinstance(response.json()["focus"], list)


def test_weekly_recap_api_returns_stale_flag(client):
    response = client.get("/api/overview/weekly-recap")

    assert "stale" in response.json()


def test_weekly_recap_refresh_returns_200(client):
    response = client.post("/api/overview/weekly-recap/refresh")

    assert response.status_code == 200


def test_weekly_recap_refresh_returns_stale_false(client):
    response = client.post("/api/overview/weekly-recap/refresh")

    assert response.json()["stale"] is False


def test_weekly_recap_refresh_returns_summary(client):
    response = client.post("/api/overview/weekly-recap/refresh")

    assert "summary" in response.json()


def test_sync_returns_200(client):
    response = client.post("/api/sync")

    assert response.status_code == 200


def test_sync_returns_synced_count(client):
    response = client.post("/api/sync")

    assert "synced" in response.json()


def test_sync_returns_integer_count(client):
    response = client.post("/api/sync")

    assert isinstance(response.json()["synced"], int)
