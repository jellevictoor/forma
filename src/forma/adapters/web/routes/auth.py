"""Strava OAuth authentication routes."""

import logging
import uuid
from datetime import datetime, timedelta, timezone, UTC

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from forma.adapters.postgres_pool import get_pool
from forma.adapters.postgres_session_repository import PostgresSessionRepository
from forma.adapters.postgres_storage import PostgresStorage
from forma.adapters.strava_client import StravaClient
from forma.config import get_settings
from forma.domain.athlete import Athlete

router = APIRouter()
logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    settings = get_settings()
    strava_auth_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={settings.strava_client_id}"
        f"&redirect_uri={settings.base_url}/auth/strava/callback"
        "&response_type=code"
        "&approval_prompt=auto"
        "&scope=read,activity:read_all"
    )
    return templates.TemplateResponse(
        request,
        "login.html",
        {"strava_auth_url": strava_auth_url},
    )


@router.get("/auth/strava")
async def strava_auth_redirect():
    settings = get_settings()
    strava_auth_url = (
        "https://www.strava.com/oauth/authorize"
        f"?client_id={settings.strava_client_id}"
        f"&redirect_uri={settings.base_url}/auth/strava/callback"
        "&response_type=code"
        "&approval_prompt=auto"
        "&scope=read,activity:read_all"
    )
    return RedirectResponse(strava_auth_url)


@router.get("/auth/strava/callback")
async def strava_callback(code: str, request: Request):
    settings = get_settings()
    pool = get_pool()

    client = StravaClient(
        client_id=settings.strava_client_id,
        client_secret=settings.strava_client_secret,
    )
    try:
        token_data = await client.authenticate(code)
    finally:
        await client.close()

    strava_athlete = token_data.get("athlete", {})
    strava_id = strava_athlete.get("id")
    access_token = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    expires_at = datetime.fromtimestamp(token_data["expires_at"], tz=timezone.utc)

    storage = PostgresStorage(pool)
    existing = await storage.get_by_strava_id(strava_id)
    is_new = existing is None

    athlete = existing
    if athlete is None:
        athlete = Athlete(
            id=str(uuid.uuid4()),
            name=f"{strava_athlete.get('firstname', '')} {strava_athlete.get('lastname', '')}".strip()
            or "Athlete",
            strava_athlete_id=strava_id,
        )

    athlete = athlete.model_copy(update={
        "strava_access_token": access_token,
        "strava_refresh_token": refresh_token,
        "strava_token_expires_at": expires_at,
        "strava_athlete_id": strava_id,
    })
    await storage.save(athlete)

    session_repo = PostgresSessionRepository(pool)
    expires = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=settings.session_lifetime_days)
    session = await session_repo.create(athlete.id, expires)

    logger.info("athlete %s logged in via Strava (new=%s)", athlete.id, is_new)

    redirect_to = "/onboarding" if is_new else "/"
    response = RedirectResponse(redirect_to, status_code=302)
    response.set_cookie(
        key="session",
        value=session.token,
        httponly=True,
        secure=settings.base_url.startswith("https"),
        samesite="lax",
        max_age=settings.session_lifetime_days * 86400,
    )
    return response


@router.post("/logout")
async def logout(request: Request):
    token = request.cookies.get("session")
    if token:
        pool = get_pool()
        session_repo = PostgresSessionRepository(pool)
        await session_repo.delete(token)

    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie("session")
    return response
