"""Workout planning routes."""

import asyncio
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates

from forma.adapters.web.dependencies import (
    get_athlete_id,
    get_athlete_profile_service,
    get_plan_adherence_service,
    get_plan_skip_service,
    get_workout_planning_service,
)
from forma.application.athlete_profile_service import AthleteProfileService
from forma.application.plan_adherence import PlanAdherenceService
from forma.application.plan_skip_service import PlanSkipService
from forma.application.workout_planning_service import WorkoutPlanningService
from forma.domain.athlete import ScheduleTemplateSlot
from forma.domain.workout import WorkoutType

router = APIRouter()
templates = Jinja2Templates(directory="src/forma/templates")

_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _day_dict(d) -> dict:
    return {
        "date": d.day.isoformat(),
        "workout_type": d.workout_type,
        "intensity": d.intensity,
        "duration_minutes": d.duration_minutes,
        "description": d.description,
        "exercises": d.exercises,
    }


@router.get("/plan", response_class=HTMLResponse)
async def plan_page(
    request: Request,
    profile_service: Annotated[AthleteProfileService, Depends(get_athlete_profile_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    athlete = await profile_service.get_profile(athlete_id)
    workout_types = [wt for wt in WorkoutType if wt != WorkoutType.REST]
    today_dow = date.today().weekday()
    sorted_slots = []
    if athlete and athlete.schedule_template:
        indexed = list(enumerate(athlete.schedule_template))
        indexed.sort(key=lambda pair: (pair[1].day_of_week - today_dow) % 7)
        sorted_slots = indexed
    return templates.TemplateResponse(
        request,
        "plan.html",
        {
            "athlete": athlete,
            "sorted_slots": sorted_slots,
            "workout_types": workout_types,
            "day_names": _DAY_NAMES,
            "day_names_enumerated": list(enumerate(_DAY_NAMES)),
            "today": date.today(),
        },
    )


@router.post("/plan/template/add")
async def add_template_slot(
    profile_service: Annotated[AthleteProfileService, Depends(get_athlete_profile_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
    workout_type: Annotated[str, Form()],
    day_of_week: Annotated[int, Form()],
    is_optional: Annotated[bool, Form()] = False,
):
    slot = ScheduleTemplateSlot(
        workout_type=WorkoutType(workout_type),
        day_of_week=day_of_week,
        is_optional=is_optional,
    )
    await profile_service.add_schedule_slot(athlete_id, slot)
    return RedirectResponse(url="/plan", status_code=303)


@router.delete("/plan/template/{slot_index}")
async def remove_template_slot(
    slot_index: int,
    profile_service: Annotated[AthleteProfileService, Depends(get_athlete_profile_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    await profile_service.remove_schedule_slot(athlete_id, slot_index)
    return JSONResponse({"status": "ok"})


@router.get("/api/plan")
async def get_plan(
    planning_service: Annotated[WorkoutPlanningService, Depends(get_workout_planning_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    cached, fitness = await asyncio.gather(
        planning_service.get_cached(athlete_id),
        planning_service.get_fitness_state(athlete_id),
    )
    if not cached:
        return JSONResponse({"cached": False, "fitness": fitness})
    return JSONResponse({
        "cached": True,
        "stale": cached.is_stale,
        "rationale": cached.rationale,
        "days": [_day_dict(d) for d in cached.days],
        "fitness": fitness,
    })


@router.post("/api/plan/refresh")
async def refresh_plan(
    planning_service: Annotated[WorkoutPlanningService, Depends(get_workout_planning_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    cached = await planning_service.generate_and_cache(athlete_id)
    fitness = await planning_service.get_fitness_state(athlete_id)
    return JSONResponse({
        "cached": True,
        "stale": False,
        "rationale": cached.rationale,
        "days": [_day_dict(d) for d in cached.days],
        "fitness": fitness,
    })


class ExercisesRequest(BaseModel):
    description: str = ""


@router.post("/api/plan/day/{day_date}/{workout_type}/exercises")
async def get_day_exercises(
    day_date: date,
    workout_type: str,
    body: ExercisesRequest,
    planning_service: Annotated[WorkoutPlanningService, Depends(get_workout_planning_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    exercises = await planning_service.get_exercises_for_day(
        athlete_id, day_date, workout_type, body.description
    )
    return JSONResponse({"exercises": exercises})


@router.post("/api/plan/day/{day_date}/{workout_type}/exercises/refresh")
async def refresh_day_exercises(
    day_date: date,
    workout_type: str,
    body: ExercisesRequest,
    planning_service: Annotated[WorkoutPlanningService, Depends(get_workout_planning_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    exercises = await planning_service.refresh_exercises_for_day(
        athlete_id, day_date, workout_type, body.description
    )
    return JSONResponse({"exercises": exercises})


@router.post("/api/plan/day/{day_date}/skip")
async def skip_plan_day(
    day_date: date,
    skip_service: Annotated[PlanSkipService, Depends(get_plan_skip_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    result = await skip_service.skip_day(athlete_id, day_date)
    return JSONResponse(result)


@router.get("/api/plan/adherence")
async def plan_adherence_api(
    adherence_service: Annotated[PlanAdherenceService, Depends(get_plan_adherence_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    adherence = await adherence_service.get_adherence(athlete_id)
    return JSONResponse({"days": adherence})


