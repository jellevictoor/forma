"""Port for persisting per-workout chat messages."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChatMessage:
    role: str  # "user" or "model"
    content: str
    created_at: datetime


class ChatRepository(ABC):
    """Stores and retrieves chat messages for a workout conversation."""

    @abstractmethod
    async def list_messages(self, workout_id: str) -> list[ChatMessage]: ...

    @abstractmethod
    async def append_message(self, workout_id: str, role: str, content: str) -> None: ...

    @abstractmethod
    async def clear_messages(self, workout_id: str) -> None: ...
