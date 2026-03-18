"""asyncpg connection pool — module-level singleton initialized at startup."""

import asyncpg
from asyncpg import Pool

_pool: Pool | None = None


async def init_pool(database_url: str) -> None:
    global _pool
    _pool = await asyncpg.create_pool(database_url)


def get_pool() -> Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized — call init_pool() first")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
