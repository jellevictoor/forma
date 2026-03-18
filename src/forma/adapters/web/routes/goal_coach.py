"""Goal coaching routes — conversational, data-grounded goal setting."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from forma.adapters.web.dependencies import (
    get_athlete_id,
    get_athlete_profile_service,
    get_goal_coaching_service,
)
from forma.application.athlete_profile_service import AthleteProfileService
from forma.application.goal_coaching_service import GoalCoachingService, GoalProposal

router = APIRouter()
templates = Jinja2Templates(directory="src/forma/templates")


class ChatRequest(BaseModel):
    message: str
    history: list[dict]  # [{role: "user"|"model", text: "..."}]


class ConfirmRequest(BaseModel):
    proposal: dict


@router.get("/profile/goal/coach", response_class=HTMLResponse)
async def goal_coach_page(
    request: Request,
    coaching_service: Annotated[GoalCoachingService, Depends(get_goal_coaching_service)],
    profile_service: Annotated[AthleteProfileService, Depends(get_athlete_profile_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    snapshot = await coaching_service.build_snapshot(athlete_id)
    athlete = await profile_service.get_profile(athlete_id)
    return templates.TemplateResponse(
        request,
        "goal_coach.html",
        {
            "athlete": athlete,
            "snapshot": snapshot,
        },
    )


@router.post("/profile/goal/coach/start")
async def goal_coach_start(
    coaching_service: Annotated[GoalCoachingService, Depends(get_goal_coaching_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    message = await coaching_service.start(athlete_id)
    return JSONResponse({"message": message})


@router.post("/profile/goal/coach/message")
async def goal_coach_message(
    body: ChatRequest,
    coaching_service: Annotated[GoalCoachingService, Depends(get_goal_coaching_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    response = await coaching_service.chat(athlete_id, body.message, body.history)
    proposal = coaching_service.extract_proposal(response)
    clean_response = response
    if proposal:
        import re
        clean_response = re.sub(r"<<GOAL_PROPOSAL>>.*?<<END_PROPOSAL>>", "", response, flags=re.DOTALL).strip()
    return JSONResponse({
        "response": clean_response,
        "proposal": _proposal_to_dict(proposal) if proposal else None,
    })


@router.post("/profile/goal/coach/confirm")
async def goal_coach_confirm(
    body: ConfirmRequest,
    coaching_service: Annotated[GoalCoachingService, Depends(get_goal_coaching_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    p = body.proposal
    proposal = GoalProposal(
        goal_type=p.get("goal_type", "general_fitness"),
        description=p.get("description", ""),
        target_value=p.get("target_value"),
        target_date=None,
        milestones=p.get("milestones", []),
        rationale=p.get("rationale", ""),
    )
    if p.get("target_date"):
        from datetime import date
        proposal.target_date = date.fromisoformat(p["target_date"])

    await coaching_service.save_proposal(athlete_id, proposal)
    return RedirectResponse(url="/profile", status_code=303)


def _proposal_to_dict(proposal: GoalProposal) -> dict:
    return {
        "goal_type": proposal.goal_type,
        "description": proposal.description,
        "target_value": proposal.target_value,
        "target_date": proposal.target_date.isoformat() if proposal.target_date else None,
        "milestones": proposal.milestones,
        "rationale": proposal.rationale,
    }
