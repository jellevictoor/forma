"""Application service for read-side analytics (CQS read model)."""

from dataclasses import dataclass
from datetime import date, timedelta

from fitness_coach.domain.fitness_freshness import CTL_SEED_DAYS, compute_fitness_freshness
from fitness_coach.domain.workout import Workout
from fitness_coach.ports.workout_analytics_repository import (
    PersonalRecord,
    SportSummary,
    WorkoutAnalyticsRepository,
)
from fitness_coach.ports.workout_repository import WorkoutRepository

PR_DISTANCES_METERS = [1000.0, 5000.0, 10000.0, 21097.0, 42195.0]
PAGE_SIZE = 20


def current_year() -> int:
    return date.today().year


@dataclass
class OverviewStats:
    sport_summaries: list[SportSummary]
    recent_workouts: list[Workout]
    weekly_volumes: list[dict]
    year: int


class AnalyticsService:
    """Handles all read-side use cases for the dashboard."""

    def __init__(
        self,
        analytics_repo: WorkoutAnalyticsRepository,
        workout_repo: WorkoutRepository,
    ) -> None:
        self._analytics = analytics_repo
        self._workouts = workout_repo

    async def overview_stats(self, athlete_id: str, year: int | None = None) -> OverviewStats:
        year = year or current_year()
        sport_summaries = await self._analytics.sport_summaries(athlete_id, year)
        recent_workouts = await self._workouts.get_recent(athlete_id, count=5)
        weekly_volumes = await self._analytics.weekly_volume(athlete_id, None, year)
        return OverviewStats(
            sport_summaries=sport_summaries,
            recent_workouts=recent_workouts,
            weekly_volumes=weekly_volumes,
            year=year,
        )

    async def weekly_volume_chart_data(
        self,
        athlete_id: str,
        workout_type: str | None = None,
        year: int | None = None,
    ) -> list[dict]:
        year = year or current_year()
        volumes = await self._analytics.weekly_volume(athlete_id, workout_type, year)
        return [
            {
                "week_start": v.week_start.isoformat(),
                "distance_km": round(v.total_distance_meters / 1000, 2),
                "duration_hours": round(v.total_duration_seconds / 3600, 2),
                "workout_count": v.workout_count,
                "workout_type": v.workout_type,
            }
            for v in volumes
        ]

    async def pace_trend_chart_data(
        self,
        athlete_id: str,
        sport: str = "run",
        year: int | None = None,
    ) -> list[dict]:
        year = year or current_year()
        return await self._analytics.pace_trend(athlete_id, sport, year)

    async def personal_records(self, athlete_id: str, year: int | None = None) -> list[PersonalRecord]:
        year = year or current_year()
        return await self._analytics.personal_records_for_run(athlete_id, PR_DISTANCES_METERS, year)

    async def activities_page(
        self,
        athlete_id: str,
        sport_filter: str | None,
        page: int,
        year: int | None = None,
    ) -> tuple[list, int]:
        year = year or current_year()
        workout_type = None if sport_filter == "all" else sport_filter
        return await self._analytics.list_workouts_paginated(
            athlete_id, workout_type, page, PAGE_SIZE, year
        )

    async def strength_frequency_chart_data(
        self,
        athlete_id: str,
        year: int | None = None,
    ) -> list[dict]:
        year = year or current_year()
        return await self._analytics.strength_frequency(athlete_id, year)

    async def climbing_history(self, athlete_id: str, year: int | None = None) -> list[dict]:
        year = year or current_year()
        return await self._analytics.climbing_sessions(athlete_id, year)

    async def progress_comparison_data(self, athlete_id: str) -> dict:
        today = date.today()
        curr_year, curr_month = today.year, today.month
        prev_month = curr_month - 1 if curr_month > 1 else 12
        prev_year = curr_year if curr_month > 1 else curr_year - 1

        current = await self._analytics.sport_stats_for_month(athlete_id, curr_year, curr_month)
        previous = await self._analytics.sport_stats_for_month(athlete_id, prev_year, prev_month)

        current_by_sport = {s["workout_type"]: s for s in current}
        previous_by_sport = {s["workout_type"]: s for s in previous}
        sports = sorted(set(list(current_by_sport) + list(previous_by_sport)))

        empty: dict = {"sessions": 0, "distance_meters": 0.0, "duration_seconds": 0, "avg_pace_min_per_km": None}

        return {
            "current_month": date(curr_year, curr_month, 1).isoformat(),
            "previous_month": date(prev_year, prev_month, 1).isoformat(),
            "sports": [
                {
                    "workout_type": sport,
                    "current": current_by_sport.get(sport, empty),
                    "previous": previous_by_sport.get(sport, empty),
                }
                for sport in sports
            ],
        }

    async def training_log_data(self, athlete_id: str, year: int | None = None) -> list[dict]:
        year = year or current_year()
        return await self._analytics.training_log(athlete_id, year)

    async def workouts_with_notes(self, athlete_id: str, year: int | None = None) -> list[dict]:
        year = year or current_year()
        return await self._analytics.workouts_with_notes(athlete_id, year)

    async def fitness_freshness_chart_data(
        self,
        athlete_id: str,
        days: int = 90,
    ) -> list[dict]:
        today = date.today()
        since = today - timedelta(days=days + CTL_SEED_DAYS)
        daily_efforts = await self._analytics.daily_effort(athlete_id, since)
        return compute_fitness_freshness(daily_efforts, days)
