"""PostgreSQL adapter for system prompts."""

from asyncpg import Pool

from forma.ports.system_prompt_repository import SystemPrompt, SystemPromptRepository


class PostgresSystemPrompts(SystemPromptRepository):

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    async def get(self, service: str) -> SystemPrompt | None:
        row = await self._pool.fetchrow(
            "SELECT service, label, text, updated_at FROM system_prompts WHERE service = $1",
            service,
        )
        if row is None:
            return None
        return SystemPrompt(
            service=row["service"],
            label=row["label"],
            text=row["text"],
            updated_at=row["updated_at"],
        )

    async def save(self, prompt: SystemPrompt) -> None:
        await self._pool.execute(
            """
            INSERT INTO system_prompts (service, label, text, updated_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (service) DO UPDATE SET
                label = EXCLUDED.label,
                text = EXCLUDED.text,
                updated_at = NOW()
            """,
            prompt.service,
            prompt.label,
            prompt.text,
        )

    async def list_all(self) -> list[SystemPrompt]:
        rows = await self._pool.fetch(
            "SELECT service, label, text, updated_at FROM system_prompts ORDER BY service"
        )
        return [
            SystemPrompt(
                service=r["service"],
                label=r["label"],
                text=r["text"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]

    async def seed_defaults(self, defaults: list[SystemPrompt]) -> None:
        for d in defaults:
            await self._pool.execute(
                """
                INSERT INTO system_prompts (service, label, text)
                VALUES ($1, $2, $3)
                ON CONFLICT (service) DO NOTHING
                """,
                d.service,
                d.label,
                d.text,
            )
