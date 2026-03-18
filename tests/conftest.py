"""Shared test fixtures."""

import pytest
import asyncpg
from testcontainers.postgres import PostgresContainer

from forma.adapters.postgres_migrations import run_migrations


@pytest.fixture(scope="session")
def pg_url():
    with PostgresContainer("postgres:16-alpine") as container:
        yield container.get_connection_url().replace("postgresql+psycopg2", "postgresql")


@pytest.fixture
async def pool(pg_url):
    p = await asyncpg.create_pool(pg_url)
    await run_migrations(p)
    yield p
    await p.execute("TRUNCATE athletes, llm_usage CASCADE")
    await p.close()
