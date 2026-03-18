"""FastAPI application factory."""

import logging
import logging.config
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from forma.logging_config import LOGGING_CONFIG

from forma.adapters.web.routes.execution import router as execution_router
from forma.adapters.web.routes.goal_coach import router as goal_coach_router
from forma.adapters.web.routes.overview import router as overview_router
from forma.adapters.web.routes.activities import router as activities_router
from forma.adapters.web.routes.analytics import router as analytics_router
from forma.adapters.web.routes.insights import router as insights_router
from forma.adapters.web.routes.plan import router as plan_router
from forma.adapters.web.routes.profile import router as profile_router
from forma.adapters.web.routes.progress import router as progress_router

STATIC_DIR = Path(__file__).parent.parent.parent / "static"

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # Apply unified log config after uvicorn has run its own setup,
    # so uvicorn loggers propagate to our root handler.
    logging.config.dictConfig(LOGGING_CONFIG)
    logger.info("forma starting up")
    yield
    logger.info("forma shutting down")


def create_app() -> FastAPI:
    app = FastAPI(title="forma", lifespan=_lifespan)

    # Add CORS middleware for home WiFi access from iOS app
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.include_router(overview_router)
    app.include_router(activities_router)
    app.include_router(analytics_router)
    app.include_router(progress_router)
    app.include_router(insights_router)
    app.include_router(profile_router)
    app.include_router(plan_router)
    app.include_router(execution_router)
    app.include_router(goal_coach_router)

    return app
