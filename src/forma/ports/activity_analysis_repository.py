"""Port for caching per-workout AI analysis."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ActivityAnalysis:
    performance_assessment: str
    training_load_context: str
    goal_relevance: str
    comparison_to_recent: str
    takeaway: str


@dataclass
class CachedActivityAnalysis:
    workout_id: str
    analysis: ActivityAnalysis
    generated_at: datetime


class ActivityAnalysisRepository(ABC):
    """Stores and retrieves cached per-workout analyses."""

    @abstractmethod
    async def get(self, workout_id: str) -> CachedActivityAnalysis | None: ...

    @abstractmethod
    async def save(self, workout_id: str, analysis: ActivityAnalysis) -> None: ...

    @abstractmethod
    async def invalidate(self, workout_id: str) -> None: ...
