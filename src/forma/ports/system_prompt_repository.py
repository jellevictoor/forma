"""Port for managing LLM system prompts."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SystemPrompt:
    service: str
    label: str
    text: str
    updated_at: datetime | None = None


class SystemPromptRepository(ABC):

    @abstractmethod
    async def get(self, service: str) -> SystemPrompt | None:
        """Return the system prompt for a service, or None if not set."""
        ...

    @abstractmethod
    async def save(self, prompt: SystemPrompt) -> None:
        """Upsert a system prompt."""
        ...

    @abstractmethod
    async def list_all(self) -> list[SystemPrompt]:
        """Return all system prompts ordered by service name."""
        ...

    @abstractmethod
    async def seed_defaults(self, defaults: list[SystemPrompt]) -> None:
        """Insert defaults that don't already exist (ON CONFLICT DO NOTHING)."""
        ...
