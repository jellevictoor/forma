"""Port for caching training insights output."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CachedInsights:
    summary: str
    patterns: list[str]
    impact: list[str]
    recommendations: list[str]
    note_count: int
    generated_at: datetime
    year: int


class InsightsCacheRepository(ABC):
    """Stores and retrieves cached training insights results."""

    @abstractmethod
    async def get(self, athlete_id: str, year: int) -> CachedInsights | None: ...

    @abstractmethod
    async def save(self, athlete_id: str, year: int, insights) -> None: ...
