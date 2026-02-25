"""Tests for analytics routes."""

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from fitness_coach.adapters.web.app import create_app
from fitness_coach.application.analytics_service import AnalyticsService


def make_mock_service() -> AnalyticsService:
    service = AsyncMock(spec=AnalyticsService)
    service.weekly_volume_chart_data = AsyncMock(return_value=[])
    service.pace_trend_chart_data = AsyncMock(return_value=[])
    return service


@pytest.fixture
def client():
    app = create_app()

    async def override_service():
        return make_mock_service()

    from fitness_coach.adapters.web.dependencies import get_analytics_service, get_athlete_id
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
