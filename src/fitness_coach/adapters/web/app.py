"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from fitness_coach.adapters.web.routes.overview import router as overview_router
from fitness_coach.adapters.web.routes.activities import router as activities_router
from fitness_coach.adapters.web.routes.analytics import router as analytics_router
from fitness_coach.adapters.web.routes.insights import router as insights_router
from fitness_coach.adapters.web.routes.plan import router as plan_router
from fitness_coach.adapters.web.routes.profile import router as profile_router
from fitness_coach.adapters.web.routes.progress import router as progress_router

STATIC_DIR = Path(__file__).parent.parent.parent / "static"


def create_app() -> FastAPI:
    app = FastAPI(title="Fitness Coach Dashboard")

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.include_router(overview_router)
    app.include_router(activities_router)
    app.include_router(analytics_router)
    app.include_router(progress_router)
    app.include_router(insights_router)
    app.include_router(profile_router)
    app.include_router(plan_router)

    return app
