"""Applies numbered SQL migrations from the migrations/ directory in order."""

import logging
from importlib.resources import files

from asyncpg import Pool

logger = logging.getLogger(__name__)

_TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


async def run_migrations(pool: Pool) -> None:
    """Create the tracking table, then apply any unapplied migrations in filename order."""
    await pool.execute(_TRACKING_TABLE)

    migrations_pkg = files("forma.migrations")
    sql_files = sorted(
        entry for entry in migrations_pkg.iterdir()
        if entry.name.endswith(".sql")
    )

    applied = {row["filename"] for row in await pool.fetch("SELECT filename FROM schema_migrations")}

    for entry in sql_files:
        if entry.name in applied:
            logger.debug("migration already applied: %s", entry.name)
            continue
        sql = entry.read_text(encoding="utf-8")
        logger.info("applying migration: %s", entry.name)
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute(sql)
                await conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES ($1)", entry.name
                )
        logger.info("migration applied: %s", entry.name)
