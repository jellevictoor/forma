"""Unified LLM caller — provider-agnostic via litellm."""

import asyncio
import logging

import litellm

logger = logging.getLogger("forma.llm")

# Suppress litellm's verbose logging
litellm.suppress_debug_info = True

DEFAULT_MODEL = "gemini/gemini-2.5-flash"

AVAILABLE_MODELS = [
    {"id": "gemini/gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "gemini", "env_key": "GEMINI_API_KEY", "input_cost": 0.15, "output_cost": 0.60, "speed": "Fast"},
    {"id": "gemini/gemini-2.5-pro", "name": "Gemini 2.5 Pro", "provider": "gemini", "env_key": "GEMINI_API_KEY", "input_cost": 1.25, "output_cost": 5.00, "speed": "Smart"},
    {"id": "anthropic/claude-sonnet-4-5-20250514", "name": "Claude Sonnet 4.5", "provider": "anthropic", "env_key": "ANTHROPIC_API_KEY", "input_cost": 3.00, "output_cost": 15.00, "speed": "Smart"},
    {"id": "anthropic/claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "provider": "anthropic", "env_key": "ANTHROPIC_API_KEY", "input_cost": 0.80, "output_cost": 4.00, "speed": "Fast"},
    {"id": "openai/gpt-4o", "name": "GPT-4o", "provider": "openai", "env_key": "OPENAI_API_KEY", "input_cost": 2.50, "output_cost": 10.00, "speed": "Smart"},
    {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai", "env_key": "OPENAI_API_KEY", "input_cost": 0.15, "output_cost": 0.60, "speed": "Fast"},
]


async def get_active_model() -> str:
    """Read the active model from DB config, fall back to DEFAULT_MODEL."""
    try:
        from forma.adapters.postgres_pool import get_pool
        pool = get_pool()
        row = await pool.fetchrow(
            "SELECT model FROM system_prompts WHERE service = '_default'"
        )
        if row and row["model"]:
            return row["model"]
    except Exception:
        pass
    return DEFAULT_MODEL


async def set_active_model(model_id: str) -> None:
    """Persist the active model choice and update the cache."""
    global _active_model_cache
    from forma.adapters.postgres_pool import get_pool
    pool = get_pool()
    await pool.execute(
        """INSERT INTO system_prompts (service, label, text, model, updated_at)
           VALUES ('_default', 'Global default', '', $1, NOW())
           ON CONFLICT (service) DO UPDATE SET model = $1, updated_at = NOW()""",
        model_id,
    )
    _active_model_cache = model_id


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


_active_model_cache: str | None = None


def _resolve_active_model() -> str:
    """Return the cached active model. Updated via set_active_model() or load_active_model()."""
    return _active_model_cache or DEFAULT_MODEL


async def load_active_model() -> str:
    """Read active model from DB and update the cache. Call at startup."""
    global _active_model_cache
    try:
        from forma.adapters.postgres_pool import get_pool
        pool = get_pool()
        row = await pool.fetchrow(
            "SELECT model FROM system_prompts WHERE service = '_default'"
        )
        if row and row["model"]:
            _active_model_cache = row["model"]
    except Exception:
        pass
    return _resolve_active_model()


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
    # Resolve active model from DB if caller passed the default
    if model == DEFAULT_MODEL:
        model = _resolve_active_model()
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
