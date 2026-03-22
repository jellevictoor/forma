"""Tests for PostgreSQL system prompts adapter."""

import pytest

from forma.adapters.postgres_system_prompts import PostgresSystemPrompts
from forma.ports.system_prompt_repository import SystemPrompt


@pytest.fixture
def repo(pool):
    return PostgresSystemPrompts(pool)


@pytest.mark.asyncio
async def test_get_returns_none_when_not_set(repo):
    result = await repo.get("nonexistent")

    assert result is None


@pytest.mark.asyncio
async def test_save_and_get_round_trip(repo):
    prompt = SystemPrompt(service="test-svc", label="Test", text="You are a test bot.")
    await repo.save(prompt)

    result = await repo.get("test-svc")

    assert result.text == "You are a test bot."


@pytest.mark.asyncio
async def test_save_overwrites_existing(repo):
    await repo.save(SystemPrompt(service="test-svc", label="Test", text="Version 1"))
    await repo.save(SystemPrompt(service="test-svc", label="Test", text="Version 2"))

    result = await repo.get("test-svc")

    assert result.text == "Version 2"


@pytest.mark.asyncio
async def test_list_all_returns_saved_prompts(repo):
    await repo.save(SystemPrompt(service="a-svc", label="A", text="Prompt A"))
    await repo.save(SystemPrompt(service="b-svc", label="B", text="Prompt B"))

    results = await repo.list_all()

    services = [r.service for r in results]
    assert "a-svc" in services
    assert "b-svc" in services


@pytest.mark.asyncio
async def test_seed_defaults_inserts_new(repo):
    defaults = [SystemPrompt(service="seed-test", label="Seed", text="Default prompt")]

    await repo.seed_defaults(defaults)

    result = await repo.get("seed-test")
    assert result.text == "Default prompt"


@pytest.mark.asyncio
async def test_seed_defaults_does_not_overwrite_existing(repo):
    await repo.save(SystemPrompt(service="seed-test2", label="Custom", text="Custom prompt"))

    await repo.seed_defaults([SystemPrompt(service="seed-test2", label="Seed", text="Default")])

    result = await repo.get("seed-test2")
    assert result.text == "Custom prompt"
