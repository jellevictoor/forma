"""Shared helpers for Gemini API calls — enforces per-user limits and logs token usage."""

import asyncio
import logging

from google import genai
from google.genai import types

logger = logging.getLogger("forma.gemini_usage")


class AIQuotaExceeded(Exception):
    """Raised when a user's AI access is disabled or their token cap is reached."""


async def check_ai_access(athlete_id: str) -> None:
    """Raise AIQuotaExceeded if the athlete has AI disabled or is over their 30-day token cap."""
    try:
        from forma.adapters.postgres_pool import get_pool
        from forma.adapters.postgres_storage import PostgresStorage
        pool = get_pool()
        athlete = await PostgresStorage(pool).get(athlete_id)
        if athlete is None:
            return
        if not athlete.ai_enabled:
            raise AIQuotaExceeded("AI access disabled for this account")
        if athlete.token_limit_30d is not None:
            row = await pool.fetchrow(
                """
                SELECT COALESCE(SUM(input_tokens + output_tokens), 0) AS total
                FROM llm_usage
                WHERE athlete_id = $1
                  AND created_at >= NOW() - INTERVAL '30 days'
                """,
                athlete_id,
            )
            used = int(row["total"])
            if used >= athlete.token_limit_30d:
                raise AIQuotaExceeded(
                    f"Token limit reached ({used:,} / {athlete.token_limit_30d:,} tokens in 30 days)"
                )
    except AIQuotaExceeded:
        raise
    except Exception as exc:
        logger.warning("failed to check AI access for %s: %s", athlete_id, exc)


def generate(
    client: genai.Client,
    model: str,
    contents,
    config: types.GenerateContentConfig | None = None,
    *,
    service: str,
    athlete_id: str | None = None,
):
    response = client.models.generate_content(model=model, contents=contents, config=config)
    _track_usage(response, service, model, athlete_id)
    return response


def _track_usage(response, service: str, model: str, athlete_id: str | None) -> None:
    meta = response.usage_metadata
    if not meta:
        return
    input_tokens = meta.prompt_token_count or 0
    output_tokens = meta.candidates_token_count or 0
    logger.info(
        "tokens [%s] %s — in=%d out=%d total=%d",
        service,
        model,
        input_tokens,
        output_tokens,
        input_tokens + output_tokens,
    )
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_persist_usage(service, model, input_tokens, output_tokens, athlete_id))
    except RuntimeError:
        pass  # no running loop — usage is logged but not persisted


async def _persist_usage(
    service: str, model: str, input_tokens: int, output_tokens: int, athlete_id: str | None
) -> None:
    try:
        from forma.adapters.postgres_pool import get_pool
        pool = get_pool()
        await pool.execute(
            "INSERT INTO llm_usage (service, model, input_tokens, output_tokens, athlete_id)"
            " VALUES ($1, $2, $3, $4, $5)",
            service,
            model,
            input_tokens,
            output_tokens,
            athlete_id,
        )
    except Exception as exc:
        logger.warning("failed to persist LLM usage: %s", exc)
