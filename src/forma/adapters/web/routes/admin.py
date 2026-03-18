"""Admin panel — ops view for the instance owner. Not linked from the main nav."""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from forma.adapters.postgres_pool import get_pool
from forma.adapters.postgres_storage import PostgresStorage
from forma.adapters.web.dependencies import get_athlete_id
from forma.domain.athlete import Role

router = APIRouter(prefix="/admin")
logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


async def _require_admin(athlete_id: str = Depends(get_athlete_id)) -> str:
    pool = get_pool()
    athlete = await PostgresStorage(pool).get(athlete_id)
    if not athlete or athlete.role != Role.SUPERADMIN:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin only")
    return athlete_id


@router.get("", response_class=HTMLResponse)
async def admin_page(
    request: Request,
    athlete_id: Annotated[str, Depends(_require_admin)],
):
    pool = get_pool()

    # All users
    athlete_rows = await pool.fetch(
        "SELECT id, data, created_at FROM athletes ORDER BY created_at ASC"
    )
    from forma.domain.athlete import Athlete
    athletes = [(Athlete.model_validate_json(r["data"]), r["created_at"]) for r in athlete_rows]

    # Token usage — 30-day totals per athlete
    usage_rows = await pool.fetch(
        """
        SELECT
            u.athlete_id,
            SUM(u.input_tokens)  AS input_tokens,
            SUM(u.output_tokens) AS output_tokens,
            COUNT(*)             AS calls
        FROM llm_usage u
        WHERE u.created_at >= NOW() - INTERVAL '30 days'
        GROUP BY u.athlete_id
        """
    )
    usage_by_athlete = {
        r["athlete_id"]: {
            "input": int(r["input_tokens"]),
            "output": int(r["output_tokens"]),
            "calls": int(r["calls"]),
        }
        for r in usage_rows
    }

    # Token usage — per service (30 days)
    service_rows = await pool.fetch(
        """
        SELECT service,
               SUM(input_tokens)  AS input_tokens,
               SUM(output_tokens) AS output_tokens,
               COUNT(*)           AS calls
        FROM llm_usage
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY service
        ORDER BY (SUM(input_tokens) + SUM(output_tokens)) DESC
        """
    )

    # Recent LLM calls
    recent_calls = await pool.fetch(
        """
        SELECT service, model, input_tokens, output_tokens, athlete_id, created_at
        FROM llm_usage
        ORDER BY created_at DESC
        LIMIT 25
        """
    )

    # System stats
    stats = await pool.fetchrow(
        """
        SELECT
            (SELECT COUNT(*) FROM workouts)  AS total_workouts,
            (SELECT COUNT(*) FROM athletes)  AS total_athletes,
            (SELECT COUNT(*) FROM llm_usage) AS total_llm_calls,
            (SELECT SUM(input_tokens) + SUM(output_tokens) FROM llm_usage
             WHERE created_at >= NOW() - INTERVAL '30 days') AS tokens_30d,
            (SELECT SUM(input_tokens * 0.15 + output_tokens * 0.60) / 1000000.0
             FROM llm_usage
             WHERE created_at >= NOW() - INTERVAL '30 days') AS cost_30d
        """
    )

    # Name lookup for recent calls
    athlete_names = {a.id: a.name for a, _ in athletes}

    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "athletes": athletes,
            "usage_by_athlete": usage_by_athlete,
            "service_rows": [dict(r) for r in service_rows],
            "recent_calls": [dict(r) for r in recent_calls],
            "stats": dict(stats),
            "athlete_names": athlete_names,
            "current_athlete_id": athlete_id,
        },
    )


@router.post("/athletes/{target_id}/block")
async def block_athlete(
    target_id: str,
    athlete_id: Annotated[str, Depends(_require_admin)],
):
    pool = get_pool()
    storage = PostgresStorage(pool)
    target = await storage.get(target_id)
    if not target:
        return JSONResponse({"error": "not found"}, status_code=404)
    await storage.save(target.model_copy(update={"is_blocked": True}))
    return JSONResponse({"status": "blocked"})


@router.post("/athletes/{target_id}/unblock")
async def unblock_athlete(
    target_id: str,
    athlete_id: Annotated[str, Depends(_require_admin)],
):
    pool = get_pool()
    storage = PostgresStorage(pool)
    target = await storage.get(target_id)
    if not target:
        return JSONResponse({"error": "not found"}, status_code=404)
    await storage.save(target.model_copy(update={"is_blocked": False}))
    return JSONResponse({"status": "unblocked"})


@router.post("/athletes/{target_id}/promote")
async def promote_athlete(
    target_id: str,
    athlete_id: Annotated[str, Depends(_require_admin)],
):
    pool = get_pool()
    storage = PostgresStorage(pool)
    target = await storage.get(target_id)
    if not target:
        return JSONResponse({"error": "not found"}, status_code=404)
    await storage.save(target.model_copy(update={"role": Role.SUPERADMIN}))
    return JSONResponse({"status": "promoted"})


@router.post("/athletes/{target_id}/demote")
async def demote_athlete(
    target_id: str,
    athlete_id: Annotated[str, Depends(_require_admin)],
):
    pool = get_pool()
    storage = PostgresStorage(pool)
    target = await storage.get(target_id)
    if not target:
        return JSONResponse({"error": "not found"}, status_code=404)
    await storage.save(target.model_copy(update={"role": Role.USER}))
    return JSONResponse({"status": "demoted"})


@router.post("/athletes/{target_id}/toggle-ai")
async def toggle_ai(
    target_id: str,
    athlete_id: Annotated[str, Depends(_require_admin)],
):
    pool = get_pool()
    storage = PostgresStorage(pool)
    target = await storage.get(target_id)
    if not target:
        return JSONResponse({"error": "not found"}, status_code=404)
    await storage.save(target.model_copy(update={"ai_enabled": not target.ai_enabled}))
    return JSONResponse({"ai_enabled": not target.ai_enabled})


@router.post("/athletes/{target_id}/token-limit")
async def set_token_limit(
    target_id: str,
    athlete_id: Annotated[str, Depends(_require_admin)],
    payload: dict,
):
    pool = get_pool()
    storage = PostgresStorage(pool)
    target = await storage.get(target_id)
    if not target:
        return JSONResponse({"error": "not found"}, status_code=404)
    raw = payload.get("limit")
    limit = int(raw) if raw not in (None, "", 0) else None
    await storage.save(target.model_copy(update={"token_limit_30d": limit}))
    return JSONResponse({"token_limit_30d": limit})


@router.delete("/athletes/{target_id}")
async def delete_athlete(
    target_id: str,
    athlete_id: Annotated[str, Depends(_require_admin)],
):
    if target_id == athlete_id:
        return JSONResponse({"error": "cannot delete yourself"}, status_code=400)
    pool = get_pool()
    await PostgresStorage(pool).delete(target_id)
    return JSONResponse({"status": "deleted"})
