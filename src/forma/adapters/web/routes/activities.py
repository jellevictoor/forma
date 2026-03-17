"""Activities listing routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates

from forma.adapters.web.dependencies import (
    get_activity_analysis_service,
    get_analytics_service,
    get_athlete_id,
    get_workout_repo,
)
from forma.application.activity_analysis_service import ActivityAnalysisService
from forma.application.analytics_service import AnalyticsService
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
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    workout = await workout_repo.get_workout(activity_id)
    cached_analysis = await analysis_service.get_cached(activity_id)
    chat_messages = await analysis_service.get_chat_messages(activity_id)

    return templates.TemplateResponse(
        request,
        "activity_detail.html",
        {"workout": workout, "cached_analysis": cached_analysis, "chat_messages": chat_messages},
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
