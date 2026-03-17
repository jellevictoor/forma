"""Tests for activities routes."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from forma.adapters.web.app import create_app
from forma.application.activity_analysis_service import ActivityAnalysisService
from forma.application.analytics_service import AnalyticsService
from forma.domain.workout import Workout, WorkoutType
from forma.ports.activity_analysis_repository import ActivityAnalysis, CachedActivityAnalysis
from forma.ports.workout_repository import WorkoutRepository


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


def make_mock_analytics_service(workouts=None, total=0) -> AnalyticsService:
    service = AsyncMock(spec=AnalyticsService)
    service.activities_page = AsyncMock(return_value=(workouts or [], total))
    return service


def make_mock_workout_repo(workout=None) -> WorkoutRepository:
    repo = AsyncMock(spec=WorkoutRepository)
    repo.get_workout = AsyncMock(return_value=workout)
    return repo


def make_mock_analysis_service(cached=None) -> ActivityAnalysisService:
    service = AsyncMock(spec=ActivityAnalysisService)
    service.get_cached = AsyncMock(return_value=cached)
    service.get_chat_messages = AsyncMock(return_value=[])
    service.generate_and_cache = AsyncMock(return_value=CachedActivityAnalysis(
        workout_id="w1",
        analysis=ActivityAnalysis(
            performance_assessment="Solid run.",
            training_load_context="You were fresh.",
            goal_relevance="On track.",
            comparison_to_recent="Faster.",
            takeaway="Keep it up.",
        ),
        generated_at=datetime.now(tz=timezone.utc),
    ))
    return service


@pytest.fixture
def client():
    app = create_app()
    from forma.adapters.web.dependencies import (
        get_activity_analysis_service,
        get_analytics_service,
        get_athlete_id,
        get_workout_repo,
    )
    app.dependency_overrides[get_analytics_service] = lambda: make_mock_analytics_service([make_workout()], 1)
    app.dependency_overrides[get_workout_repo] = lambda: make_mock_workout_repo(make_workout())
    app.dependency_overrides[get_activity_analysis_service] = lambda: make_mock_analysis_service()
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


def test_analyse_endpoint_returns_200(client):
    response = client.post("/activities/detail/w1/analyse")

    assert response.status_code == 200


def test_analyse_endpoint_returns_json_with_takeaway(client):
    response = client.post("/activities/detail/w1/analyse")
    data = response.json()

    assert data["takeaway"] == "Keep it up."


def test_analyse_endpoint_returns_all_fields(client):
    response = client.post("/activities/detail/w1/analyse")
    data = response.json()

    assert "performance_assessment" in data
    assert "training_load_context" in data
    assert "goal_relevance" in data
    assert "comparison_to_recent" in data
