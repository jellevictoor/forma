"""Onboarding flow for new users."""

import logging
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from forma.adapters.web.dependencies import get_athlete_id, get_athlete_profile_service
from forma.application.athlete_profile_service import AthleteProfileService

router = APIRouter(prefix="/onboarding")
logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@router.get("", response_class=HTMLResponse)
async def onboarding_profile(
    request: Request,
    athlete_id: str = Depends(get_athlete_id),
    service: AthleteProfileService = Depends(get_athlete_profile_service),
):
    athlete = await service.get_profile(athlete_id)
    return templates.TemplateResponse(
        request,
        "onboarding.html",
        {"step": 1, "athlete": athlete},
    )


@router.post("/profile")
async def save_profile(
    request: Request,
    athlete_id: str = Depends(get_athlete_id),
    service: AthleteProfileService = Depends(get_athlete_profile_service),
    name: str = Form(""),
    date_of_birth: str = Form(""),
    weight_kg: str = Form(""),
    height_cm: str = Form(""),
    max_heartrate: str = Form(""),
):
    updates = {"name": name.strip()} if name.strip() else {}
    if date_of_birth:
        updates["date_of_birth"] = date.fromisoformat(date_of_birth)
    if weight_kg:
        updates["weight_kg"] = float(weight_kg)
    if height_cm:
        updates["height_cm"] = float(height_cm)
    if max_heartrate:
        updates["max_heartrate"] = int(max_heartrate)

    if updates:
        await service.update_profile(athlete_id, updates)

    return RedirectResponse("/onboarding/sync", status_code=303)


@router.get("/sync", response_class=HTMLResponse)
async def onboarding_sync(
    request: Request,
    athlete_id: str = Depends(get_athlete_id),
):
    return templates.TemplateResponse(
        request,
        "onboarding.html",
        {"step": 2},
    )


@router.get("/goal", response_class=HTMLResponse)
async def onboarding_goal(
    request: Request,
    athlete_id: str = Depends(get_athlete_id),
):
    return templates.TemplateResponse(
        request,
        "onboarding.html",
        {"step": 3},
    )


@router.post("/complete")
async def onboarding_complete(athlete_id: str = Depends(get_athlete_id)):
    return RedirectResponse("/", status_code=303)
