"""Overview dashboard routes."""

import asyncio
import json
import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import StreamingResponse

from forma.adapters.web.dependencies import (
    get_analytics_service,
    get_athlete_id,
    get_athlete_profile_service,
    get_strava_sync,
    get_weekly_recap_service,
)
from forma.application.analytics_service import AnalyticsService
from forma.application.athlete_profile_service import AthleteProfileService
from forma.application.sync_all_activities import FullStravaSync, SyncProgress
from forma.application.weekly_recap import WeeklyRecapService

router = APIRouter()
templates = Jinja2Templates(directory="src/forma/templates")


@router.get("/", response_class=HTMLResponse)
async def overview_page(
    request: Request,
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    profile_service: Annotated[AthleteProfileService, Depends(get_athlete_profile_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    stats, athlete = await asyncio.gather(
        service.overview_stats(athlete_id),
        profile_service.get_profile(athlete_id),
    )
    return templates.TemplateResponse(request, "overview.html", {
        "stats": stats,
        "today": date.today(),
        "goal": athlete.primary_goal,
    })


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
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    cached = await recap_service.get_cached(athlete_id)
    if not cached:
        return {"cached": False}

    return {
        "cached": True,
        "stale": cached.is_stale,
        "summary": cached.summary,
        "highlight": cached.highlight,
        "form_note": cached.form_note,
        "focus": cached.focus,
    }


@router.get("/api/sync/stream")
async def sync_stream(
    sync: Annotated[FullStravaSync, Depends(get_strava_sync)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    queue: asyncio.Queue[str | None] = asyncio.Queue()

    async def on_progress(progress: SyncProgress) -> None:
        event = json.dumps({
            "synced": progress.synced,
            "skipped": progress.skipped,
            "activity": progress.activity_name,
            "phase": progress.phase,
        })
        await queue.put(f"data: {event}\n\n")

    async def run_sync() -> None:
        try:
            synced = await sync.execute(athlete_id, on_progress=on_progress)
            done = json.dumps({"done": True, "synced": synced})
            await queue.put(f"data: {done}\n\n")
        except Exception as exc:
            error = json.dumps({"error": str(exc)})
            await queue.put(f"data: {error}\n\n")
        finally:
            await queue.put(None)

    async def event_generator():
        task = asyncio.create_task(run_sync())
        try:
            while True:
                msg = await queue.get()
                if msg is None:
                    break
                yield msg
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/api/sync/status")
async def sync_status(
    athlete_service: Annotated[AthleteProfileService, Depends(get_athlete_profile_service)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    athlete = await athlete_service.get_profile(athlete_id)
    return {
        "sync_state": athlete.sync_state.value if athlete else "never_synced",
        "backfill_cursor": athlete.backfill_cursor.isoformat() if athlete and athlete.backfill_cursor else None,
    }


@router.post("/api/sync/resume-backfill")
async def resume_backfill_api(
    sync: Annotated[FullStravaSync, Depends(get_strava_sync)],
    athlete_id: Annotated[str, Depends(get_athlete_id)],
):
    asyncio.create_task(_run_backfill(sync, athlete_id))
    return {"status": "started"}


async def _run_backfill(sync: FullStravaSync, athlete_id: str) -> None:
    try:
        await sync.resume_backfill(athlete_id)
    except Exception:
        logger = logging.getLogger(__name__)
        logger.exception("background backfill failed for athlete %s", athlete_id)


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
