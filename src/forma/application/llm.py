"""Unified LLM caller — provider-agnostic via litellm."""

import asyncio
import logging

import litellm

logger = logging.getLogger("forma.llm")

# Suppress litellm's verbose logging
litellm.suppress_debug_info = True

DEFAULT_MODEL = "gemini/gemini-2.5-flash"
GLOBAL_DEFAULT_SERVICE = "_default"


async def get_global_default_model() -> str:
    """Read the global default model from DB, or fall back to hardcoded."""
    try:
        from forma.adapters.postgres_pool import get_pool
        from forma.adapters.postgres_system_prompts import PostgresSystemPrompts
        pool = get_pool()
        repo = PostgresSystemPrompts(pool)
        prompt = await repo.get(GLOBAL_DEFAULT_SERVICE)
        if prompt and prompt.model:
            return prompt.model
    except Exception:
        pass
    return DEFAULT_MODEL


class AIQuotaExceeded(Exception):
    """Raised when a user's AI access is disabled or their token cap is reached."""


async def check_ai_access(athlete_id: str) -> None:
    """Raise AIQuotaExceeded if the athlete has AI disabled or is over their 30-day token cap."""
    try:
        from forma.adapters.postgres_pool import get_pool
        pool = get_pool()
        row = await pool.fetchrow(
            "SELECT ai_enabled, token_limit_30d FROM athletes WHERE id = $1",
            athlete_id,
        )
        if row is None:
            return
        if not row["ai_enabled"]:
            raise AIQuotaExceeded("AI access disabled for this account")
        if row["token_limit_30d"] is not None:
            usage = await pool.fetchrow(
                """
                SELECT COALESCE(SUM(input_tokens + output_tokens), 0) AS total
                FROM llm_usage
                WHERE athlete_id = $1
                  AND created_at >= NOW() - INTERVAL '30 days'
                """,
                athlete_id,
            )
            used = int(usage["total"])
            if used >= row["token_limit_30d"]:
                raise AIQuotaExceeded(
                    f"Token limit reached ({used:,} / {row['token_limit_30d']:,} tokens in 30 days)"
                )
    except AIQuotaExceeded:
        raise
    except Exception as exc:
        logger.warning("failed to check AI access for %s: %s", athlete_id, exc)


def generate(
    *,
    model: str = DEFAULT_MODEL,
    system: str | None = None,
    prompt: str | None = None,
    messages: list[dict] | None = None,
    service: str,
    athlete_id: str | None = None,
) -> str:
    """Call an LLM and return the response text.

    Use `prompt` for simple single-turn calls.
    Use `messages` for multi-turn conversations (OpenAI format: role/content).
    """
    msgs = _build_messages(system, prompt, messages)
    response = litellm.completion(model=model, messages=msgs)
    text = response.choices[0].message.content or ""
    _track_usage(response, service, model, athlete_id)
    return text


def _build_messages(
    system: str | None,
    prompt: str | None,
    messages: list[dict] | None,
) -> list[dict]:
    result = []
    if system:
        result.append({"role": "system", "content": system})
    if messages:
        result.extend(messages)
    if prompt:
        result.append({"role": "user", "content": prompt})
    return result


def _track_usage(response, service: str, model: str, athlete_id: str | None) -> None:
    usage = response.usage
    if not usage:
        return
    input_tokens = usage.prompt_tokens or 0
    output_tokens = usage.completion_tokens or 0
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
        pass


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
