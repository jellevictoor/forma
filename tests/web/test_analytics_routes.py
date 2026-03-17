"""Tests for analytics routes."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from forma.adapters.web.app import create_app
from forma.application.analytics_service import AnalyticsService


def make_mock_service() -> AnalyticsService:
    service = AsyncMock(spec=AnalyticsService)
    service.weekly_volume_chart_data = AsyncMock(return_value=[])
    service.pace_trend_chart_data = AsyncMock(return_value=[])
    service.unified_volume_chart_data = AsyncMock(return_value=[])
    return service


# Add pace_trend_for_range to the analytics repo mock
def make_analytics_repo_mock():
    repo = AsyncMock()
    repo.pace_trend_for_range = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def client():
    app = create_app()

    async def override_service():
        return make_mock_service()

    from forma.adapters.web.dependencies import get_analytics_service, get_athlete_id
    app.dependency_overrides[get_analytics_service] = override_service
    app.dependency_overrides[get_athlete_id] = lambda: "athlete1"
    return TestClient(app)


def test_analytics_run_page_returns_200(client):
    response = client.get("/analytics/run")

    assert response.status_code == 200


def test_analytics_strength_page_returns_200(client):
    response = client.get("/analytics/strength")

    assert response.status_code == 200


def test_analytics_climbing_page_returns_200(client):
    response = client.get("/analytics/climbing")

    assert response.status_code == 200


def test_analytics_volume_api_returns_json(client):
    response = client.get("/api/analytics/run/volume")

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]


def test_analytics_pace_trend_api_returns_json(client):
    response = client.get("/api/analytics/run/pace-trend")

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]


def test_unified_volume_api_returns_json(client):
    response = client.get("/api/analytics/volume/3m")

    assert response.status_code == 200


def test_unified_volume_api_invalid_months_defaults_to_3(client):
    response = client.get("/api/analytics/volume/99m")

    assert response.status_code == 200


def test_sport_volume_range_endpoint_returns_200(client):
    response = client.get("/api/analytics/run/volume/3m")

    assert response.status_code == 200


def test_pace_trend_range_endpoint_returns_200(client):
    response = client.get("/api/analytics/run/pace-trend/3m")

    assert response.status_code == 200
