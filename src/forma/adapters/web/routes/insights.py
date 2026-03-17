"""Training insights route — private note analysis."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from forma.adapters.web.dependencies import get_athlete_id, get_insights_service
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
    cached = await service.get_cached(athlete_id, year)
    return templates.TemplateResponse(
        request, "insights.html", {"cached": cached, "year": year}
    )


@router.post("/insights/refresh")
async def insights_refresh(
    service: Annotated[TrainingInsightsService, Depends(get_insights_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    year = date.today().year
    await service.generate_and_cache(athlete_id, year)
    return RedirectResponse(url="/insights", status_code=303)
