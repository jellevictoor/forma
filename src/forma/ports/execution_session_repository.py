"""Port for storing and retrieving workout execution sessions."""

from abc import ABC, abstractmethod

from forma.domain.execution_session import ExecutionSession


class ExecutionSessionRepository(ABC):
    """Stores and retrieves workout execution sessions."""

    @abstractmethod
    async def save(self, session: ExecutionSession) -> None:
        """Persist a session."""
        ...

    @abstractmethod
    async def get(self, session_id: str) -> ExecutionSession | None:
        """Retrieve a session by ID."""
        ...

    @abstractmethod
    async def get_active_for_athlete(self, athlete_id: str) -> ExecutionSession | None:
        """Retrieve the active (not completed) session for an athlete, if any."""
        ...
