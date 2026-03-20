"""Read-side port for workout analytics queries."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class WeeklyVolume:
    week_start: date
    total_distance_meters: float
    total_duration_seconds: int
    workout_count: int
    workout_type: str | None


@dataclass
class PersonalRecord:
    workout_type: str
    distance_meters: float
    duration_seconds: int
    pace_min_per_km: float
    achieved_on: date
    workout_id: str


@dataclass
class SportSummary:
    workout_type: str
    total_workouts: int
    total_distance_meters: float
    total_duration_seconds: int
    most_recent: date | None


class WorkoutAnalyticsRepository(ABC):
    """Read-side port for analytics queries — separate from CRUD operations."""

    @abstractmethod
    async def weekly_volume(
        self,
        athlete_id: str,
        workout_type: str | None,
        year: int,
    ) -> list[WeeklyVolume]:
        """Return weekly volume aggregates for the given year."""

    @abstractmethod
    async def weekly_volume_for_range(
        self,
        athlete_id: str,
        since: date,
        until: date,
    ) -> list[WeeklyVolume]:
        """Return weekly volume aggregates for all sports within a date range."""

    @abstractmethod
    async def personal_records_for_run(
        self,
        athlete_id: str,
        distances_meters: list[float],
    ) -> list[PersonalRecord]:
        """Return the best (fastest) effort for each distance bucket, all time."""

    @abstractmethod
    async def pace_trend(
        self,
        athlete_id: str,
        workout_type: str,
        year: int,
    ) -> list[dict]:
        """Return weekly average pace (min/km) for the given sport and year."""

    @abstractmethod
    async def pace_trend_for_range(
        self,
        athlete_id: str,
        workout_type: str,
        since: date,
        until: date,
    ) -> list[dict]:
        """Return weekly average pace (min/km) for the given sport within a date range."""

    @abstractmethod
    async def sport_summaries(self, athlete_id: str, year: int) -> list[SportSummary]:
        """Return a summary row per sport for the given year."""

    @abstractmethod
    async def list_workouts_paginated(
        self,
        athlete_id: str,
        workout_type: str | None,
        page: int,
        page_size: int,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list, int]:
        """Return (workouts, total_count) for the given page, optionally filtered by date range."""

    @abstractmethod
    async def strength_frequency(
        self,
        athlete_id: str,
        year: int,
    ) -> list[dict]:
        """Return weekly strength session counts for the given year."""

    @abstractmethod
    async def climbing_sessions(self, athlete_id: str, year: int) -> list[dict]:
        """Return all climbing sessions for the given year."""

    @abstractmethod
    async def workouts_with_notes(self, athlete_id: str, year: int) -> list[dict]:
        """Return all workouts that have a non-empty private note."""

    @abstractmethod
    async def sport_stats_for_month(self, athlete_id: str, year: int, month: int) -> list[dict]:
        """Return per-sport stats for a specific calendar month.

        Each dict has: workout_type, sessions, distance_meters,
        duration_seconds, avg_pace_min_per_km (None for non-running sports).
        """

    @abstractmethod
    async def training_log(self, athlete_id: str, year: int) -> list[dict]:
        """Return all workouts for the year as lightweight dicts for the calendar heatmap.

        Each dict has: id, date (ISO str), workout_type, duration_seconds,
        distance_meters, name.
        """

    @abstractmethod
    async def daily_effort(self, athlete_id: str, since: date) -> list[dict]:
        """Return daily total effort scores since the given date.

        Each dict has 'date' (str ISO) and 'effort' (float).
        Effort uses HR-based TRIMP when heart rate is available, else duration in minutes.
        """

    @abstractmethod
    async def distinct_sport_types(self, athlete_id: str) -> list[str]:
        """Return all distinct workout_type values for the athlete, ordered by frequency."""

    @abstractmethod
    async def runs_with_hr(
        self,
        athlete_id: str,
        since: date,
        until: date,
    ) -> list[dict]:
        """Return runs with HR data in a date range.

        Each dict has: moving_time_seconds (int), average_heartrate (float).
        """

    @abstractmethod
    async def recent_same_type_summary(
        self,
        athlete_id: str,
        workout_type: str,
        exclude_id: str,
        count: int = 4,
    ) -> list[dict]:
        """Return recent workouts of the same type for cross-session comparison.

        Each dict has: date (str ISO), duration_minutes (float), avg_hr (float|None).
        Ordered most-recent first. Excludes the workout with exclude_id.
        """
