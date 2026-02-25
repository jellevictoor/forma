"""Tests for plan routes."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from fitness_coach.adapters.web.app import create_app
from fitness_coach.application.athlete_profile_service import AthleteProfileService
from fitness_coach.application.workout_planning_service import WorkoutPlanningService
from fitness_coach.domain.athlete import Athlete
from fitness_coach.ports.plan_cache_repository import CachedWeeklyPlan, PlannedDay


def make_athlete() -> Athlete:
    return Athlete(id="athlete1", name="Jane Doe")


def make_cached_plan() -> CachedWeeklyPlan:
    return CachedWeeklyPlan(
        days=[
            PlannedDay(
                day=date.today(),
                workout_type="run",
                intensity="easy",
                duration_minutes=45,
                description="Easy recovery run.",
            )
        ],
        rationale="Focus on recovery this week.",
        generated_at=datetime.now(tz=timezone.utc),
        latest_activity_at=None,
        is_stale=False,
    )


def make_mock_planning_service(cached: CachedWeeklyPlan | None = None) -> WorkoutPlanningService:
    service = AsyncMock(spec=WorkoutPlanningService)
    service.get_cached = AsyncMock(return_value=cached)
    service.generate_and_cache = AsyncMock(return_value=make_cached_plan())
    sections = {"warmup": ["5 min jog"], "main": ["3x10 squats"], "cooldown": ["stretch"]}
    service.get_exercises_for_day = AsyncMock(return_value=sections)
    service.refresh_exercises_for_day = AsyncMock(return_value=sections)
    return service


def make_mock_profile_service() -> AthleteProfileService:
    service = AsyncMock(spec=AthleteProfileService)
    service.get_profile = AsyncMock(return_value=make_athlete())
    service.add_schedule_slot = AsyncMock(return_value=make_athlete())
    service.remove_schedule_slot = AsyncMock(return_value=make_athlete())
    return service


@pytest.fixture
def client():
    app = create_app()

    from fitness_coach.adapters.web.dependencies import (
        get_athlete_id,
        get_athlete_profile_service,
        get_workout_planning_service,
    )

    app.dependency_overrides[get_athlete_id] = lambda: "athlete1"
    app.dependency_overrides[get_athlete_profile_service] = lambda: make_mock_profile_service()
    app.dependency_overrides[get_workout_planning_service] = lambda: make_mock_planning_service(
        cached=make_cached_plan()
    )

    return TestClient(app)


@pytest.fixture
def client_no_cache():
    app = create_app()

    from fitness_coach.adapters.web.dependencies import (
        get_athlete_id,
        get_athlete_profile_service,
        get_workout_planning_service,
    )

    app.dependency_overrides[get_athlete_id] = lambda: "athlete1"
    app.dependency_overrides[get_athlete_profile_service] = lambda: make_mock_profile_service()
    app.dependency_overrides[get_workout_planning_service] = lambda: make_mock_planning_service(
        cached=None
    )

    return TestClient(app)


def test_plan_page_returns_200(client):
    response = client.get("/plan")

    assert response.status_code == 200


def test_plan_page_returns_html(client):
    response = client.get("/plan")

    assert "text/html" in response.headers["content-type"]


def test_plan_api_returns_cached_false_when_no_plan(client_no_cache):
    response = client_no_cache.get("/api/plan")

    assert response.json()["cached"] is False


def test_plan_api_returns_cached_true_when_plan_exists(client):
    response = client.get("/api/plan")

    assert response.json()["cached"] is True


def test_plan_api_returns_days_list(client):
    response = client.get("/api/plan")

    assert isinstance(response.json()["days"], list)


def test_plan_api_returns_stale_flag(client):
    response = client.get("/api/plan")

    assert "stale" in response.json()


def test_plan_api_returns_rationale(client):
    response = client.get("/api/plan")

    assert "rationale" in response.json()


def test_plan_refresh_returns_200(client):
    response = client.post("/api/plan/refresh")

    assert response.status_code == 200


def test_plan_refresh_returns_stale_false(client):
    response = client.post("/api/plan/refresh")

    assert response.json()["stale"] is False


def test_plan_refresh_returns_days_list(client):
    response = client.post("/api/plan/refresh")

    assert isinstance(response.json()["days"], list)


def test_exercises_endpoint_returns_200(client):
    today = date.today().isoformat()
    response = client.post(
        f"/api/plan/day/{today}/strength/exercises",
        json={"description": "45-minute strength session focused on lower body"},
    )

    assert response.status_code == 200


def test_exercises_endpoint_returns_dict(client):
    today = date.today().isoformat()
    response = client.post(
        f"/api/plan/day/{today}/strength/exercises",
        json={"description": "45-minute strength session focused on lower body"},
    )

    assert isinstance(response.json()["exercises"], dict)


def test_exercises_refresh_endpoint_returns_200(client):
    today = date.today().isoformat()
    response = client.post(
        f"/api/plan/day/{today}/strength/exercises/refresh",
        json={"description": "Strength session"},
    )

    assert response.status_code == 200


def test_exercises_refresh_endpoint_returns_dict(client):
    today = date.today().isoformat()
    response = client.post(
        f"/api/plan/day/{today}/strength/exercises/refresh",
        json={"description": "Strength session"},
    )

    assert isinstance(response.json()["exercises"], dict)


def test_add_template_slot_redirects(client):
    response = client.post(
        "/plan/template/add",
        data={"workout_type": "run", "day_of_week": "0"},
        follow_redirects=False,
    )

    assert response.status_code == 303


def test_delete_template_slot_returns_ok(client):
    response = client.delete("/plan/template/0")

    assert response.json()["status"] == "ok"
