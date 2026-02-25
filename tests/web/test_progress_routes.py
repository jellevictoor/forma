"""Tests for progress routes."""

from unittest.mock import AsyncMock
from datetime import date

import pytest
from fastapi.testclient import TestClient

from fitness_coach.adapters.web.app import create_app
from fitness_coach.application.analytics_service import AnalyticsService
from fitness_coach.ports.workout_analytics_repository import PersonalRecord


def make_mock_service() -> AnalyticsService:
    service = AsyncMock(spec=AnalyticsService)
    service.personal_records = AsyncMock(
        return_value=[
            PersonalRecord("run", 5000, 1500, 5.0, date(2026, 2, 16), "w1"),
        ]
    )
    service.strength_frequency_chart_data = AsyncMock(return_value=[])
    service.climbing_history = AsyncMock(return_value=[])
    service.fitness_freshness_chart_data = AsyncMock(return_value=[
        {"date": "2026-02-16", "fitness": 42.0, "fatigue": 55.0, "form": -13.0, "effort": 80.0}
    ])
    service.progress_comparison_data = AsyncMock(return_value={
        "current_month": "2026-02-01",
        "previous_month": "2026-01-01",
        "sports": [],
    })
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


def test_progress_page_returns_200(client):
    response = client.get("/progress")

    assert response.status_code == 200


def test_progress_page_is_html(client):
    response = client.get("/progress")

    assert "text/html" in response.headers["content-type"]


def test_personal_records_api_returns_json(client):
    response = client.get("/api/progress/personal-records")

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]


def test_personal_records_api_returns_list(client):
    response = client.get("/api/progress/personal-records")

    assert isinstance(response.json(), list)


def test_strength_frequency_api_returns_json(client):
    response = client.get("/api/progress/strength-frequency")

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]


def test_fitness_freshness_api_returns_json(client):
    response = client.get("/api/progress/fitness-freshness")

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]


def test_fitness_freshness_api_returns_list(client):
    response = client.get("/api/progress/fitness-freshness")

    assert isinstance(response.json(), list)


def test_monthly_comparison_api_returns_200(client):
    response = client.get("/api/progress/monthly-comparison")

    assert response.status_code == 200


def test_monthly_comparison_api_contains_sports_key(client):
    response = client.get("/api/progress/monthly-comparison")

    assert "sports" in response.json()
