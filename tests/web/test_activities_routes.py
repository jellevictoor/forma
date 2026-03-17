"""Tests for activities routes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from forma.adapters.web.app import create_app
from forma.application.analytics_service import AnalyticsService
from forma.domain.workout import Workout, WorkoutType


def make_workout(workout_id: str = "w1") -> Workout:
    return Workout(
        id=workout_id,
        athlete_id="athlete1",
        workout_type=WorkoutType.RUN,
        name="Morning run",
        start_time=datetime(2026, 2, 16, 9, 0, tzinfo=timezone.utc),
        duration_seconds=3600,
        distance_meters=10000,
        moving_time_seconds=3600,
    )


def make_mock_service(workouts=None, total=0) -> AnalyticsService:
    service = AsyncMock(spec=AnalyticsService)
    service.activities_page = AsyncMock(return_value=(workouts or [], total))
    return service


@pytest.fixture
def client():
    app = create_app()

    async def override_service():
        return make_mock_service([make_workout()], 1)

    from forma.adapters.web.dependencies import get_analytics_service, get_athlete_id
    app.dependency_overrides[get_analytics_service] = override_service
    app.dependency_overrides[get_athlete_id] = lambda: "athlete1"
    return TestClient(app, follow_redirects=True)


def test_activities_list_returns_200(client):
    response = client.get("/activities/all/1")

    assert response.status_code == 200


def test_activities_list_is_html(client):
    response = client.get("/activities/all/1")

    assert "text/html" in response.headers["content-type"]


def test_activities_redirect_from_root(client):
    response = client.get("/activities")

    assert response.status_code == 200
    assert "/activities/all/1" in str(response.url)


def test_activities_filtered_by_sport(client):
    response = client.get("/activities/run/1")

    assert response.status_code == 200


def test_activity_detail_returns_200(client):
    response = client.get("/activities/detail/w1")

    assert response.status_code == 200
