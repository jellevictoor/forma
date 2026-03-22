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


@router.get("/api/progress/zone-trend")
async def zone_trend_api(
    workout_repo: Annotated[WorkoutRepository, Depends(get_workout_repo)],
    athlete_service: Annotated[AthleteProfileService, Depends(get_athlete_profile_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    """Weekly HR zone distribution for the last 12 weeks."""
    from datetime import date, timedelta
    from forma.domain.workout import WorkoutType

    athlete = await athlete_service.get_profile(athlete_id)
    max_hr = athlete.max_heartrate or (220 - athlete.age if athlete and athlete.age else 185)

    since = date.today() - timedelta(weeks=12)
    workouts = await workout_repo.list_workouts_for_athlete(athlete_id, start_date=since, limit=500)
    runs = [w for w in workouts if w.workout_type == WorkoutType.RUN and w.average_heartrate]

    # Group by week
    weeks: dict[date, list] = {}
    for w in runs:
        week_start = w.start_time.date() - timedelta(days=w.start_time.weekday())
        weeks.setdefault(week_start, []).append(w)

    result = []
    for week_start in sorted(weeks):
        zone_seconds = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for w in weeks[week_start]:
            pct = w.average_heartrate / max_hr * 100
            if pct < 60:
                zone = 1
            elif pct < 70:
                zone = 2
            elif pct < 80:
                zone = 3
            elif pct < 90:
                zone = 4
            else:
                zone = 5
            zone_seconds[zone] += w.moving_time_seconds or w.duration_seconds
        total = sum(zone_seconds.values()) or 1
        result.append({
            "week": week_start.isoformat(),
            "z1_pct": round(zone_seconds[1] / total * 100),
            "z2_pct": round(zone_seconds[2] / total * 100),
            "z3_pct": round(zone_seconds[3] / total * 100),
            "z4_pct": round(zone_seconds[4] / total * 100),
            "z5_pct": round(zone_seconds[5] / total * 100),
        })
    return result


@router.get("/api/progress/long-runs")
async def long_runs_api(
    workout_repo: Annotated[WorkoutRepository, Depends(get_workout_repo)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    from datetime import date, timedelta
    since = date.today() - timedelta(days=365)
    workouts = await workout_repo.list_workouts_for_athlete(athlete_id, start_date=since, limit=500)
    return long_run_summary(workouts)
