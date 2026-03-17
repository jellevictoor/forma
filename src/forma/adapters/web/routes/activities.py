"""Activities listing routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from forma.adapters.web.dependencies import get_analytics_service, get_athlete_id
from forma.application.analytics_service import AnalyticsService

router = APIRouter()
templates = Jinja2Templates(directory="src/forma/templates")

VALID_SPORTS = {"all", "run", "strength", "climbing"}


@router.get("/activities", response_class=RedirectResponse)
async def activities_redirect():
    return RedirectResponse(url="/activities/all/1")


@router.get("/activities/detail/{activity_id}", response_class=HTMLResponse)
async def activity_detail(
    request: Request,
    activity_id: str,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    workouts, _ = await service.activities_page(athlete_id, None, 1)
    workout = next((w for w in workouts if w.id == activity_id), None)

    return templates.TemplateResponse(request, "activity_detail.html", {"workout": workout})


@router.get("/activities/{sport}/{page}", response_class=HTMLResponse)
async def activities_page(
    request: Request,
    sport: str,
    page: int,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    if sport not in VALID_SPORTS:
        return RedirectResponse(url="/activities/all/1")

    workouts, total = await service.activities_page(athlete_id, sport, page)
    total_pages = max(1, (total + 19) // 20)

    return templates.TemplateResponse(
        request,
        "activities.html",
        {
            "workouts": workouts,
            "sport": sport,
            "page": page,
            "total": total,
            "total_pages": total_pages,
        },
    )
