"""Progress and PRs routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from forma.adapters.web.dependencies import get_analytics_service, get_athlete_id, get_athlete_profile_service, get_workout_repo
from forma.application.analytics_service import AnalyticsService
from forma.application.athlete_profile_service import AthleteProfileService
from forma.domain.long_run import long_run_summary
from forma.ports.workout_repository import WorkoutRepository

router = APIRouter()
templates = Jinja2Templates(directory="src/forma/templates")


@router.get("/progress", response_class=HTMLResponse)
async def progress_page(
    request: Request,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    return templates.TemplateResponse(request, "progress.html", {})


@router.get("/api/progress/personal-records")
async def personal_records_api(
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    records = await service.personal_records(athlete_id)
    return [
        {
            "distance_meters": r.distance_meters,
            "duration_seconds": r.duration_seconds,
            "pace_min_per_km": r.pace_min_per_km,
            "achieved_on": r.achieved_on.isoformat(),
            "workout_id": r.workout_id,
        }
        for r in records
    ]


@router.get("/api/progress/strength-frequency")
async def strength_frequency_api(
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    return await service.strength_frequency_chart_data(athlete_id)


@router.get("/api/progress/monthly-comparison")
async def monthly_comparison_api(
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    return await service.progress_comparison_data(athlete_id)


@router.get("/api/progress/fitness-freshness")
async def fitness_freshness_api(
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_service: Annotated[AthleteProfileService, Depends(get_athlete_profile_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    athlete = await athlete_service.get_profile(athlete_id)
    max_hr = athlete.max_heartrate or (220 - athlete.age if athlete and athlete.age else 185)
    return await service.fitness_freshness_chart_data(athlete_id, max_hr=max_hr)


@router.get("/api/progress/long-runs")
async def long_runs_api(
    workout_repo: Annotated[WorkoutRepository, Depends(get_workout_repo)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    from datetime import date, timedelta
    since = date.today() - timedelta(days=365)
    workouts = await workout_repo.list_workouts_for_athlete(athlete_id, start_date=since, limit=500)
    return long_run_summary(workouts)
