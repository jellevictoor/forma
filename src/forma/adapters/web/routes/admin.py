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
    row = await pool.fetchrow("SELECT role FROM athletes WHERE id = $1", athlete_id)
    if not row or row["role"] != Role.SUPERADMIN.value:
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
    from forma.adapters.postgres_storage import _ATHLETE_COLUMNS, _athlete_from_row
    athlete_rows = await pool.fetch(
        f"SELECT {_ATHLETE_COLUMNS}, created_at FROM athletes ORDER BY created_at ASC"
    )
    athletes = [(_athlete_from_row(r), r["created_at"]) for r in athlete_rows]

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
            (SELECT SUM(
                CASE
                    WHEN model LIKE 'anthropic/claude-sonnet%' THEN input_tokens * 3.0 + output_tokens * 15.0
                    WHEN model LIKE 'anthropic/claude-haiku%' THEN input_tokens * 0.8 + output_tokens * 4.0
                    WHEN model LIKE 'openai/gpt-4o-mini%' THEN input_tokens * 0.15 + output_tokens * 0.60
                    WHEN model LIKE 'openai/gpt-4o%' THEN input_tokens * 2.5 + output_tokens * 10.0
                    WHEN model LIKE 'gemini%pro%' THEN input_tokens * 1.25 + output_tokens * 5.0
                    ELSE input_tokens * 0.15 + output_tokens * 0.60
                END
             ) / 1000000.0
             FROM llm_usage
             WHERE created_at >= NOW() - INTERVAL '30 days') AS cost_30d
        """
    )

    # Name lookup for recent calls
    athlete_names = {a.id: a.name for a, _ in athletes}

    # Daily AI cost — last 30 days
    daily_cost_rows = await pool.fetch(
        """
        SELECT DATE(created_at) AS day,
               SUM(
                CASE
                    WHEN model LIKE 'anthropic/claude-sonnet%' THEN input_tokens * 3.0 + output_tokens * 15.0
                    WHEN model LIKE 'anthropic/claude-haiku%' THEN input_tokens * 0.8 + output_tokens * 4.0
                    WHEN model LIKE 'openai/gpt-4o-mini%' THEN input_tokens * 0.15 + output_tokens * 0.60
                    WHEN model LIKE 'openai/gpt-4o%' THEN input_tokens * 2.5 + output_tokens * 10.0
                    WHEN model LIKE 'gemini%pro%' THEN input_tokens * 1.25 + output_tokens * 5.0
                    ELSE input_tokens * 0.15 + output_tokens * 0.60
                END
               ) / 1000000.0 AS cost,
               SUM(input_tokens + output_tokens) AS tokens,
               COUNT(*) AS calls
        FROM llm_usage
        WHERE created_at >= NOW() - INTERVAL '30 days'
        GROUP BY DATE(created_at)
        ORDER BY day
        """
    )
    daily_cost = [
        {"date": r["day"].isoformat(), "cost": float(r["cost"] or 0), "tokens": int(r["tokens"] or 0), "calls": int(r["calls"])}
        for r in daily_cost_rows
    ]

    # Daily active users — last 30 days (users who synced or had AI calls)
    dau_rows = await pool.fetch(
        """
        SELECT day, COUNT(DISTINCT athlete_id) AS users FROM (
            SELECT DATE(start_time) AS day, athlete_id FROM workouts
            WHERE start_time >= NOW() - INTERVAL '30 days'
            UNION ALL
            SELECT DATE(created_at) AS day, athlete_id FROM llm_usage
            WHERE created_at >= NOW() - INTERVAL '30 days' AND athlete_id IS NOT NULL
        ) t
        GROUP BY day ORDER BY day
        """
    )
    daily_active = [{"date": r["day"].isoformat(), "users": int(r["users"])} for r in dau_rows]

    # Per-user last activity date + workout count
    user_health_rows = await pool.fetch(
        """
        SELECT athlete_id,
               MAX(start_time) AS last_activity,
               COUNT(*) AS workout_count
        FROM workouts
        GROUP BY athlete_id
        """
    )
    user_health = {
        r["athlete_id"]: {
            "last_activity": r["last_activity"].isoformat() if r["last_activity"] else None,
            "workout_count": int(r["workout_count"]),
        }
        for r in user_health_rows
    }

    # Exercise catalog stats
    exercise_stats = await pool.fetch(
        """
        SELECT name, COUNT(*) AS cnt, MAX(plan_date) AS last_used
        FROM exercise_catalog
        GROUP BY name ORDER BY cnt DESC LIMIT 20
        """
    )
    exercise_by_category = await pool.fetch(
        """
        SELECT category, COUNT(*) AS cnt
        FROM exercise_catalog
        GROUP BY category ORDER BY cnt DESC
        """
    )
    exercise_total = await pool.fetchval(
        "SELECT COUNT(*) FROM exercise_catalog"
    )
    exercise_unique = await pool.fetchval(
        "SELECT COUNT(DISTINCT name) FROM exercise_catalog"
    )

    # User feedback
    feedback_count = await pool.fetchval("SELECT COUNT(*) FROM feedback") or 0
    feedback_rows = await pool.fetch(
        """
        SELECT f.athlete_id, f.page, f.message, f.created_at
        FROM feedback f
        ORDER BY f.created_at DESC
        LIMIT 20
        """
    )

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
            "daily_cost_json": daily_cost,
            "daily_active_json": daily_active,
            "user_health": user_health,
            "exercise_stats": [dict(r) for r in exercise_stats],
            "exercise_by_category": [dict(r) for r in exercise_by_category],
            "exercise_total": exercise_total or 0,
            "exercise_unique": exercise_unique or 0,
            "feedback": [dict(r) for r in feedback_rows],
            "feedback_count": feedback_count,
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
