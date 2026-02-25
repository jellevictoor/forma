"""Analytics routes with d3 chart data endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from fitness_coach.adapters.web.dependencies import get_analytics_service, get_athlete_id
from fitness_coach.application.analytics_service import AnalyticsService

router = APIRouter()
templates = Jinja2Templates(directory="src/fitness_coach/templates")

VALID_SPORTS = {"run", "strength", "climbing"}


@router.get("/analytics/{sport}", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    sport: str,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    if sport not in VALID_SPORTS:
        sport = "run"

    return templates.TemplateResponse(request, "analytics.html", {"sport": sport})


@router.get("/api/analytics/{sport}/volume")
async def analytics_volume_api(
    sport: str,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    return await service.weekly_volume_chart_data(athlete_id, sport)


@router.get("/api/analytics/{sport}/pace-trend")
async def analytics_pace_trend_api(
    sport: str,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    return await service.pace_trend_chart_data(athlete_id, sport)
