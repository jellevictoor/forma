"""Smoke tests — hit every page with real DI wiring to catch integration regressions.

These tests use a real PostgreSQL database (via testcontainers) and the real
application factory with no mocks. They verify that every route loads without
crashing, catching missing attributes, broken DI wiring, and template errors.
"""

import json
import os
from datetime import datetime, timezone

import asyncpg
import pytest
from fastapi.testclient import TestClient

from forma.adapters.postgres_migrations import run_migrations
from forma.adapters.web.app import create_app

ATHLETE_ID = "smoke-test-athlete"


@pytest.fixture(scope="module")
def _seed_db(pg_url):
    """Run migrations and seed test data before the app starts."""
    import asyncio

    async def _seed():
        pool = await asyncpg.create_pool(pg_url)
        await run_migrations(pool)

        # Seed athlete (minimal required columns)
        await pool.execute(
            """INSERT INTO athletes (id, name, role, goals, injuries, goal_history,
               schedule_template, equipment, preferred_workout_days)
               VALUES ($1, 'Smoke Tester', 'superadmin', '[]', '[]', '[]', '[]', '[]', '[]')
               ON CONFLICT (id) DO NOTHING""",
            ATHLETE_ID,
        )

        # Seed workout
        workout_data = json.dumps({
            "workout_type": "run", "name": "Smoke test run",
            "athlete_id": ATHLETE_ID,
            "start_time": datetime.now(tz=timezone.utc).isoformat(),
            "duration_seconds": 1800, "distance_meters": 5000,
            "description": "", "private_note": "", "id": "smoke-workout-1",
        })
        await pool.execute(
            """INSERT INTO workouts (id, athlete_id, data, start_time, workout_type, duration_seconds, distance_meters)
               VALUES ($1, $2, $3, NOW(), 'run', 1800, 5000)
               ON CONFLICT (id) DO NOTHING""",
            "smoke-workout-1", ATHLETE_ID, workout_data,
        )

        # Seed system prompts
        for svc, label in [
            ("activity-analysis", "Activity analysis"),
            ("goal-coach", "Goal coaching"),
            ("insights", "Training insights"),
            ("plan", "Workout planning"),
        ]:
            await pool.execute(
                """INSERT INTO system_prompts (service, label, text)
                   VALUES ($1, $2, 'Test prompt.')
                   ON CONFLICT (service) DO NOTHING""",
                svc, label,
            )

        await pool.close()

    asyncio.get_event_loop_policy().new_event_loop().run_until_complete(_seed())


@pytest.fixture(scope="module")
def client(pg_url, _seed_db):
    """Create a real app against a real database — no mocks."""
    os.environ["DEV_ATHLETE_ID"] = ATHLETE_ID
    os.environ["DATABASE_URL"] = pg_url

    app = create_app()
    with TestClient(app) as c:
        yield c

    os.environ.pop("DEV_ATHLETE_ID", None)
    os.environ.pop("DATABASE_URL", None)


# ── HTML pages ────────────────────────────────────────────────

def test_overview_page(client):
    assert client.get("/").status_code == 200


def test_activities_list(client):
    assert client.get("/activities/all/1").status_code == 200


def test_activities_redirect(client):
    r = client.get("/activities", follow_redirects=True)
    assert r.status_code == 200


def test_analytics_page(client):
    assert client.get("/analytics/run").status_code == 200


def test_progress_page(client):
    assert client.get("/progress").status_code == 200


def test_insights_page(client):
    assert client.get("/insights").status_code == 200


def test_plan_page(client):
    assert client.get("/plan").status_code == 200


def test_goal_page(client):
    assert client.get("/goal").status_code == 200


def test_profile_page(client):
    assert client.get("/profile").status_code == 200


def test_admin_page(client):
    assert client.get("/admin").status_code == 200


def test_activity_detail(client):
    assert client.get("/activities/detail/smoke-workout-1").status_code == 200


# ── JSON API endpoints ────────────────────────────────────────

def test_api_weekly_volume(client):
    assert client.get("/api/overview/weekly-volume").status_code == 200


def test_api_training_log(client):
    assert client.get("/api/overview/training-log").status_code == 200


def test_api_sync_status(client):
    assert client.get("/api/sync/status").status_code == 200


def test_api_alerts(client):
    assert client.get("/api/overview/alerts").status_code == 200


def test_api_zone2_compliance(client):
    assert client.get("/api/overview/zone2-compliance").status_code == 200


def test_api_plan(client):
    assert client.get("/api/plan").status_code == 200


def test_api_plan_adherence(client):
    assert client.get("/api/plan/adherence").status_code == 200


def test_api_personal_records(client):
    assert client.get("/api/progress/personal-records").status_code == 200


def test_api_strength_frequency(client):
    assert client.get("/api/progress/strength-frequency").status_code == 200


def test_api_monthly_comparison(client):
    assert client.get("/api/progress/monthly-comparison").status_code == 200


def test_api_fitness_freshness(client):
    assert client.get("/api/progress/fitness-freshness").status_code == 200


def test_api_analytics_volume(client):
    assert client.get("/api/analytics/run/volume").status_code == 200


def test_api_analytics_pace(client):
    assert client.get("/api/analytics/run/pace-trend").status_code == 200


def test_api_activity_context(client):
    assert client.get("/activities/detail/smoke-workout-1/context").status_code == 200
