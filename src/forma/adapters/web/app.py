"""FastAPI application factory."""

import logging
import logging.config
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from forma.application.llm import AIQuotaExceeded
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from forma.logging_config import LOGGING_CONFIG

from forma.adapters.web.routes.admin import router as admin_router
from forma.adapters.web.routes.auth import router as auth_router
from forma.adapters.web.routes.onboarding import router as onboarding_router
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
    logging.config.dictConfig(LOGGING_CONFIG)
    logger.info("forma starting up")

    # Sentry error tracking
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        import sentry_sdk
        sentry_sdk.init(
            dsn=sentry_dsn,
            send_default_pii=True,
            traces_sample_rate=0.1,
            release=_COMMIT_HASH,
            environment="production" if not _DEV_MODE else "development",
        )
        logger.info("sentry initialized")

    from forma.config import get_settings
    from forma.adapters.postgres_pool import init_pool, close_pool
    from forma.adapters.postgres_migrations import run_migrations

    settings = get_settings()
    if settings.database_url:
        await init_pool(settings.database_url)
        pool = _get_pool_safe()
        if pool:
            await run_migrations(pool)
            from forma.adapters.postgres_system_prompts import PostgresSystemPrompts
            from forma.application.seed_system_prompts import seed as seed_prompts
            await seed_prompts(PostgresSystemPrompts(pool))
        logger.info("database ready")
    else:
        logger.warning("DATABASE_URL not set — running without PostgreSQL")

    yield

    await close_pool()
    logger.info("forma shutting down")


def _get_git_hash() -> str:
    """Return short git commit hash from env (Docker) or git (local dev)."""
    env_hash = os.environ.get("GIT_COMMIT")
    if env_hash and env_hash != "unknown":
        return env_hash[:7]
    try:
        import subprocess
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "unknown"


_COMMIT_HASH = _get_git_hash()
_DEV_MODE = bool(os.environ.get("DEV_ATHLETE_ID"))


class _SuperadminMiddleware(BaseHTTPMiddleware):
    """Injects request.state.is_superadmin for use in templates."""

    async def dispatch(self, request: Request, call_next):
        request.state.is_superadmin = False
        request.state.commit_hash = _COMMIT_HASH
        request.state.dev_mode = _DEV_MODE
        token = request.cookies.get("session")
        if token:
            try:
                from forma.adapters.postgres_pool import get_pool as _get_pool
                from forma.adapters.postgres_session_repository import PostgresSessionRepository
                pool = _get_pool()
                session = await PostgresSessionRepository(pool).get_by_token(token)
                if session:
                    row = await pool.fetchrow(
                        "SELECT role FROM athletes WHERE id = $1", session.athlete_id
                    )
                    if row and row["role"] == "superadmin":
                        request.state.is_superadmin = True
            except Exception:  # noqa: BLE001
                pass
        return await call_next(request)


def _get_pool_safe():
    try:
        from forma.adapters.postgres_pool import get_pool
        return get_pool()
    except RuntimeError:
        return None


def create_app() -> FastAPI:
    app = FastAPI(title="forma", lifespan=_lifespan)

    app.add_middleware(_SuperadminMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if exc.status_code == 401:
            return RedirectResponse("/login", status_code=302)
        raise exc

    @app.exception_handler(AIQuotaExceeded)
    async def ai_quota_handler(request: Request, exc: AIQuotaExceeded):
        return JSONResponse(
            status_code=403,
            content={"error": "ai_quota_exceeded", "message": str(exc)},
        )

    @app.exception_handler(Exception)
    async def llm_error_handler(request: Request, exc: Exception):
        # Catch litellm rate limit errors (they raise litellm.RateLimitError)
        exc_name = type(exc).__name__
        if "RateLimitError" in exc_name or "429" in str(exc):
            logger.warning("LLM rate limit: %s", exc)
            return JSONResponse(
                status_code=429,
                content={"error": "quota_exceeded", "message": "AI API rate limit exceeded. Please try again later."},
            )
        raise exc

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok", "commit": _COMMIT_HASH}

    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    app.include_router(admin_router)
    app.include_router(auth_router)
    app.include_router(onboarding_router)
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
