"""Profile management routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from fitness_coach.adapters.web.dependencies import (
    get_athlete_id,
    get_athlete_profile_service,
    get_weight_tracking_service,
)
from fitness_coach.application.athlete_profile_service import AthleteProfileService
from fitness_coach.application.weight_tracking_service import WeightTrackingService
from fitness_coach.domain.athlete import Goal, GoalType

router = APIRouter()
templates = Jinja2Templates(directory="src/fitness_coach/templates")


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    profile_service: Annotated[AthleteProfileService, Depends(get_athlete_profile_service)],
    weight_service: Annotated[WeightTrackingService, Depends(get_weight_tracking_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    athlete = await profile_service.get_profile(athlete_id)
    weight_history = await weight_service.get_history(athlete_id, limit=10)
    chart_data = await weight_service.chart_data(athlete_id)
    is_stale = await weight_service.is_stale(athlete_id)
    goal_types = [gt for gt in GoalType]
    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            "athlete": athlete,
            "weight_history": weight_history,
            "chart_data": chart_data,
            "is_stale": is_stale,
            "goal_types": goal_types,
        },
    )


@router.post("/profile")
async def update_profile(
    profile_service: Annotated[AthleteProfileService, Depends(get_athlete_profile_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
    name: Annotated[str, Form()],
    notes: Annotated[str, Form()] = "",
    height_cm: Annotated[float | None, Form()] = None,
    experience_years: Annotated[float, Form()] = 0.0,
    max_hours_per_week: Annotated[float | None, Form()] = None,
):
    updates: dict = {
        "name": name,
        "notes": notes,
        "height_cm": height_cm,
        "experience_years": experience_years,
        "max_hours_per_week": max_hours_per_week,
    }
    await profile_service.update_profile(athlete_id, updates)
    return RedirectResponse(url="/profile", status_code=303)


@router.post("/profile/goal")
async def set_goal(
    profile_service: Annotated[AthleteProfileService, Depends(get_athlete_profile_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
    goal_type: Annotated[str, Form()],
    description: Annotated[str, Form()],
    target_value: Annotated[str, Form()] = "",
):
    goal = Goal(
        goal_type=GoalType(goal_type),
        description=description,
        target_value=target_value or None,
    )
    await profile_service.set_primary_goal(athlete_id, goal)
    return RedirectResponse(url="/profile", status_code=303)


@router.delete("/profile/goal")
async def remove_goal(
    profile_service: Annotated[AthleteProfileService, Depends(get_athlete_profile_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    await profile_service.remove_primary_goal(athlete_id)
    return JSONResponse({"status": "ok"})


@router.post("/profile/goal/advice")
async def goal_advice(
    profile_service: Annotated[AthleteProfileService, Depends(get_athlete_profile_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    advice = await profile_service.get_goal_advice(athlete_id)
    return JSONResponse(
        {
            "summary": advice.summary,
            "training_tips": advice.training_tips,
            "weekly_focus": advice.weekly_focus,
        }
    )


@router.post("/profile/weight")
async def add_weight(
    weight_service: Annotated[WeightTrackingService, Depends(get_weight_tracking_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
    weight_kg: Annotated[float, Form()],
    notes: Annotated[str, Form()] = "",
):
    await weight_service.record_weight(athlete_id, weight_kg, notes)
    return RedirectResponse(url="/profile", status_code=303)


@router.delete("/profile/weight/{entry_id}")
async def delete_weight_entry(
    entry_id: str,
    weight_service: Annotated[WeightTrackingService, Depends(get_weight_tracking_service)],
):
    await weight_service.delete_entry(entry_id)
    return JSONResponse({"status": "ok"})
