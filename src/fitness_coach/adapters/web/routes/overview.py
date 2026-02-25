"""Overview dashboard routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from fitness_coach.adapters.web.dependencies import (
    get_analytics_service,
    get_athlete_id,
    get_strava_sync,
    get_weekly_recap_service,
    get_workout_repo,
)
from fitness_coach.application.analytics_service import AnalyticsService
from fitness_coach.application.sync_all_activities import FullStravaSync
from fitness_coach.application.weekly_recap import WeeklyRecapService
from fitness_coach.ports.workout_repository import WorkoutRepository

router = APIRouter()
templates = Jinja2Templates(directory="src/fitness_coach/templates")


@router.get("/", response_class=HTMLResponse)
async def overview_page(
    request: Request,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    stats = await service.overview_stats(athlete_id)
    return templates.TemplateResponse(request, "overview.html", {"stats": stats})


@router.get("/api/overview/weekly-volume")
async def weekly_volume_api(
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    return await service.weekly_volume_chart_data(athlete_id)


@router.get("/api/overview/training-log")
async def training_log_api(
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    return await service.training_log_data(athlete_id)


@router.get("/api/overview/weekly-recap")
async def weekly_recap_api(
    recap_service: Annotated[WeeklyRecapService, Depends(get_weekly_recap_service)],
    workout_repo: Annotated[WorkoutRepository, Depends(get_workout_repo)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    cached = await recap_service.get_cached(athlete_id)
    if not cached:
        return {"cached": False}

    recent = await workout_repo.get_recent(athlete_id, count=1)
    latest_at = recent[0].start_time if recent else None
    stale = (
        latest_at is not None
        and cached.latest_activity_at is not None
        and latest_at > cached.latest_activity_at
    )

    return {
        "cached": True,
        "stale": stale,
        "summary": cached.summary,
        "highlight": cached.highlight,
        "form_note": cached.form_note,
        "focus": cached.focus,
    }


@router.post("/api/sync")
async def sync_api(
    sync: Annotated[FullStravaSync, Depends(get_strava_sync)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    synced = await sync.execute(athlete_id)
    return {"synced": synced}


@router.post("/api/overview/weekly-recap/refresh")
async def weekly_recap_refresh_api(
    recap_service: Annotated[WeeklyRecapService, Depends(get_weekly_recap_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    cached = await recap_service.generate_and_cache(athlete_id)
    return {
        "cached": True,
        "stale": False,
        "summary": cached.summary,
        "highlight": cached.highlight,
        "form_note": cached.form_note,
        "focus": cached.focus,
    }
