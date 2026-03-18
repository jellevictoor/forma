"""Analytics routes with d3 chart data endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from forma.adapters.web.dependencies import get_analytics_service, get_athlete_id
from forma.application.analytics_service import AnalyticsService

router = APIRouter()
templates = Jinja2Templates(directory="src/forma/templates")

VALID_SPORTS = {"run", "strength", "climbing", "yoga", "hike", "walk", "swim", "bike", "cross_training"}


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


@router.get("/api/analytics/volume/{months}m")
async def unified_volume_api(
    months: int,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    return await service.unified_volume_chart_data(athlete_id, months)


@router.get("/api/analytics/{sport}/volume/{months}m")
async def analytics_volume_range_api(
    sport: str,
    months: int,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    return await service.weekly_volume_chart_data(athlete_id, sport, months=months)


@router.get("/api/analytics/{sport}/volume")
async def analytics_volume_api(
    sport: str,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    return await service.weekly_volume_chart_data(athlete_id, sport)


@router.get("/api/analytics/{sport}/pace-trend/{months}m")
async def analytics_pace_trend_range_api(
    sport: str,
    months: int,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    return await service.pace_trend_chart_data(athlete_id, sport, months=months)


@router.get("/api/analytics/{sport}/pace-trend")
async def analytics_pace_trend_api(
    sport: str,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    return await service.pace_trend_chart_data(athlete_id, sport)
