"""Training insights route — private note analysis."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from forma.adapters.web.dependencies import get_insights_service, get_athlete_id
from forma.application.training_insights import TrainingInsightsService

router = APIRouter()
templates = Jinja2Templates(directory="src/forma/templates")


@router.get("/insights", response_class=HTMLResponse)
async def insights_page(
    request: Request,
    service: Annotated[TrainingInsightsService, Depends(get_insights_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    year = date.today().year
    insights = await service.analyse(athlete_id, year)
    return templates.TemplateResponse(request, "insights.html", {"insights": insights, "year": year})
