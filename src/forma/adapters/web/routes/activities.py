"""Activities listing routes."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates

from forma.adapters.web.dependencies import (
    get_activity_analysis_service,
    get_activity_stream_service,
    get_analytics_service,
    get_athlete_id,
    get_athlete_profile_service,
    get_workout_repo,
)
from forma.application.activity_analysis_service import ActivityAnalysisService
from forma.application.activity_stream_service import ActivityStreamService
from forma.application.analytics_service import AnalyticsService
from forma.application.athlete_profile_service import AthleteProfileService
from forma.ports.workout_repository import WorkoutRepository

router = APIRouter()
templates = Jinja2Templates(directory="src/forma/templates")

VALID_SPORTS = {"all", "run", "strength", "climbing"}


class ChatRequest(BaseModel):
    message: str


@router.get("/activities", response_class=RedirectResponse)
async def activities_redirect():
    return RedirectResponse(url="/activities/all/1")


@router.get("/activities/detail/{activity_id}", response_class=HTMLResponse)
async def activity_detail(
    request: Request,
    activity_id: str,
    workout_repo: Annotated[WorkoutRepository, Depends(get_workout_repo)],
    analysis_service: Annotated[ActivityAnalysisService, Depends(get_activity_analysis_service)],
    athlete_service: Annotated[AthleteProfileService, Depends(get_athlete_profile_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    workout = await workout_repo.get_workout(activity_id)
    if workout and workout.strava_raw:
        updates = {}
        if workout.average_heartrate is None and workout.strava_raw.get("average_heartrate"):
            updates["average_heartrate"] = float(workout.strava_raw["average_heartrate"])
        if workout.max_heartrate is None and workout.strava_raw.get("max_heartrate"):
            updates["max_heartrate"] = float(workout.strava_raw["max_heartrate"])
        if updates:
            workout = workout.model_copy(update=updates)
    cached_analysis = await analysis_service.get_cached(activity_id)
    chat_messages = await analysis_service.get_chat_messages(activity_id)
    athlete = await athlete_service.get_profile(athlete_id)

    return templates.TemplateResponse(
        request,
        "activity_detail.html",
        {
            "workout": workout,
            "cached_analysis": cached_analysis,
            "chat_messages": chat_messages,
            "athlete": athlete,
        },
    )


@router.post("/activities/detail/{activity_id}/analyse")
async def analyse_activity(
    activity_id: str,
    analysis_service: Annotated[ActivityAnalysisService, Depends(get_activity_analysis_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    try:
        cached = await analysis_service.generate_and_cache(athlete_id, activity_id)
        a = cached.analysis
        return JSONResponse({
            "performance_assessment": a.performance_assessment,
            "training_load_context": a.training_load_context,
            "goal_relevance": a.goal_relevance,
            "comparison_to_recent": a.comparison_to_recent,
            "takeaway": a.takeaway,
        })
    except ValueError:
        return JSONResponse({"error": "Workout not found"}, status_code=404)


@router.post("/activities/detail/{activity_id}/chat")
async def chat_about_activity(
    activity_id: str,
    body: ChatRequest,
    analysis_service: Annotated[ActivityAnalysisService, Depends(get_activity_analysis_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    try:
        response = await analysis_service.chat(athlete_id, activity_id, body.message)
        return JSONResponse({"response": response})
    except ValueError:
        return JSONResponse({"error": "Workout not found"}, status_code=404)


@router.get("/activities/detail/{activity_id}/context")
async def activity_context(
    activity_id: str,
    workout_repo: Annotated[WorkoutRepository, Depends(get_workout_repo)],
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    workout = await workout_repo.get_workout(activity_id)
    if not workout:
        return JSONResponse({"error": "not found"}, status_code=404)

    calories = None
    calories_estimated = False
    if workout.strava_raw:
        calories = workout.strava_raw.get("calories")
    if not calories and workout.average_heartrate and workout.duration_seconds:
        # MET-based: strength/climbing ≈ 4.0 MET, 70 kg default body weight
        calories = round(4.0 * 70 * workout.duration_seconds / 3600)
        calories_estimated = True
    elif calories:
        calories_estimated = False

    recent = await service.recent_same_type_summary(
        athlete_id, workout.workout_type.value, activity_id, count=4
    )
    return JSONResponse({
        "calories": calories,
        "calories_estimated": calories_estimated,
        "recent": recent,
    })


@router.get("/activities/detail/{activity_id}/streams")
async def activity_streams(
    activity_id: str,
    stream_service: Annotated[ActivityStreamService, Depends(get_activity_stream_service)],
):
    try:
        streams = await stream_service.get_or_fetch(activity_id)
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
    if not streams or (not streams.latlng and not streams.heartrate):
        return JSONResponse({"error": "No stream data available"}, status_code=404)
    return JSONResponse({
        "latlng": streams.latlng,
        "time": streams.time,
        "velocity_smooth": streams.velocity_smooth,
        "heartrate": streams.heartrate,
        "has_hr": bool(streams.heartrate),
        "has_gps": bool(streams.latlng),
    })


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
            "today": date.today(),
            "date_from_str": "",
            "date_to_str": "",
        },
    )


@router.get("/activities/{sport}/{from_date}/{to_date}/{page}", response_class=HTMLResponse)
async def activities_page_filtered(
    request: Request,
    sport: str,
    from_date: str,
    to_date: str,
    page: int,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    if sport not in VALID_SPORTS:
        return RedirectResponse(url="/activities/all/1")

    try:
        date_from = date.fromisoformat(from_date)
        date_to = date.fromisoformat(to_date)
    except ValueError:
        return RedirectResponse(url=f"/activities/{sport}/1")

    workouts, total = await service.activities_page(athlete_id, sport, page, date_from, date_to)
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
            "today": date.today(),
            "date_from_str": from_date,
            "date_to_str": to_date,
        },
    )
