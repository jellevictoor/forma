"""Application service for read-side analytics (CQS read model)."""

from dataclasses import dataclass
from datetime import date, timedelta

from forma.domain.fitness_freshness import CTL_SEED_DAYS, compute_fitness_freshness
from forma.domain.hr_zones import compute_zone2_bounds
from forma.domain.workout import Workout
from forma.ports.workout_analytics_repository import (
    PersonalRecord,
    SportSummary,
    WorkoutAnalyticsRepository,
)
from forma.ports.workout_repository import WorkoutRepository

PR_DISTANCES_METERS = [1000.0, 5000.0, 10000.0, 21097.0, 42195.0]
PAGE_SIZE = 20


SPORTS = ("run", "strength", "climbing", "yoga", "hike", "walk", "swim", "bike", "cross_training")
VALID_MONTHS = {3, 6, 12}


def _week_spine(year: int) -> list[date]:
    """Return every Monday (ISO week start) that overlaps the given year."""
    jan1 = date(year, 1, 1)
    first_monday = jan1 - timedelta(days=jan1.weekday())
    weeks: list[date] = []
    current = first_monday
    dec31 = date(year, 12, 31)
    while current <= dec31:
        weeks.append(current)
        current += timedelta(weeks=1)
    return weeks


def _date_range_spine(since: date, until: date) -> list[date]:
    """Return every Monday between since and until (inclusive)."""
    first_monday = since - timedelta(days=since.weekday())
    weeks: list[date] = []
    current = first_monday
    while current <= until:
        weeks.append(current)
        current += timedelta(weeks=1)
    return weeks


def current_year() -> int:
    return date.today().year


@dataclass
class OverviewStats:
    sport_summaries: list[SportSummary]
    recent_workouts: list[Workout]
    weekly_volumes: list[dict]
    personal_records: list[PersonalRecord]
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
        personal_records = await self._analytics.personal_records_for_run(athlete_id, PR_DISTANCES_METERS)
        return OverviewStats(
            sport_summaries=sport_summaries,
            recent_workouts=recent_workouts,
            weekly_volumes=weekly_volumes,
            personal_records=personal_records,
            year=year,
        )

    async def weekly_volume_chart_data(
        self,
        athlete_id: str,
        workout_type: str | None = None,
        year: int | None = None,
        months: int | None = None,
    ) -> list[dict]:
        if months is not None:
            return await self._weekly_volume_for_months(
                athlete_id, workout_type, months
            )
        year = year or current_year()
        volumes = await self._analytics.weekly_volume(athlete_id, workout_type, year)
        result = self._volumes_to_dicts(volumes)
        if not workout_type:
            return result
        return self._fill_weekly_volume_gaps(result, workout_type, year)

    async def _weekly_volume_for_months(
        self,
        athlete_id: str,
        workout_type: str | None,
        months: int,
    ) -> list[dict]:
        if months not in VALID_MONTHS:
            months = 3
        today = date.today()
        since = today - timedelta(days=months * 30)
        until = today + timedelta(days=1)
        volumes = await self._analytics.weekly_volume_for_range(
            athlete_id, since, until
        )
        if workout_type:
            volumes = [v for v in volumes if v.workout_type == workout_type]
        result = self._volumes_to_dicts(volumes)
        if not workout_type:
            return result
        return self._fill_weekly_volume_gaps_for_range(
            result, workout_type, since, today
        )

    @staticmethod
    def _volumes_to_dicts(volumes: list) -> list[dict]:
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

    async def unified_volume_chart_data(
        self,
        athlete_id: str,
        months: int = 3,
    ) -> list[dict]:
        if months not in VALID_MONTHS:
            months = 3
        today = date.today()
        since = today - timedelta(days=months * 30)
        until = today + timedelta(days=1)
        volumes = await self._analytics.weekly_volume_for_range(
            athlete_id, since, until
        )
        by_week_sport: dict[str, dict[str, float]] = {}
        for v in volumes:
            key = v.week_start.isoformat()
            if key not in by_week_sport:
                by_week_sport[key] = {}
            sport = v.workout_type or "other"
            by_week_sport[key][sport] = round(v.total_duration_seconds / 3600, 2)

        spine = _date_range_spine(since, today)
        return [
            {
                "week_start": w.isoformat(),
                **{
                    f"{s}_hours": by_week_sport.get(w.isoformat(), {}).get(s, 0.0)
                    for s in SPORTS
                },
            }
            for w in spine
        ]

    async def pace_trend_chart_data(
        self,
        athlete_id: str,
        sport: str = "run",
        year: int | None = None,
        months: int | None = None,
    ) -> list[dict]:
        if months is not None:
            if months not in VALID_MONTHS:
                months = 3
            today = date.today()
            since = today - timedelta(days=months * 30)
            until = today + timedelta(days=1)
            return await self._analytics.pace_trend_for_range(
                athlete_id, sport, since, until
            )
        year = year or current_year()
        return await self._analytics.pace_trend(athlete_id, sport, year)

    async def personal_records(self, athlete_id: str) -> list[PersonalRecord]:
        return await self._analytics.personal_records_for_run(athlete_id, PR_DISTANCES_METERS)

    async def recent_same_type_summary(
        self, athlete_id: str, workout_type: str, exclude_id: str, count: int = 4
    ) -> list[dict]:
        return await self._analytics.recent_same_type_summary(
            athlete_id, workout_type, exclude_id, count
        )

    async def available_sport_types(self, athlete_id: str) -> list[str]:
        return await self._analytics.distinct_sport_types(athlete_id)

    async def activities_page(
        self,
        athlete_id: str,
        sport_filter: str | None,
        page: int,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> tuple[list, int]:
        workout_type = None if sport_filter == "all" else sport_filter
        return await self._analytics.list_workouts_paginated(
            athlete_id, workout_type, page, PAGE_SIZE, date_from, date_to
        )

    async def strength_frequency_chart_data(
        self,
        athlete_id: str,
        year: int | None = None,
    ) -> list[dict]:
        year = year or current_year()
        rows = await self._analytics.strength_frequency(athlete_id, year)
        return self._fill_weekly_strength_gaps(rows, year)

    @staticmethod
    def _fill_weekly_volume_gaps(
        data: list[dict], workout_type: str, year: int
    ) -> list[dict]:
        by_week = {d["week_start"]: d for d in data}
        empty = {
            "distance_km": 0.0,
            "duration_hours": 0.0,
            "workout_count": 0,
            "workout_type": workout_type,
        }
        return [
            by_week.get(
                w.isoformat(), {"week_start": w.isoformat(), **empty}
            )
            for w in _week_spine(year)
        ]

    @staticmethod
    def _fill_weekly_volume_gaps_for_range(
        data: list[dict], workout_type: str, since: date, until: date
    ) -> list[dict]:
        by_week = {d["week_start"]: d for d in data}
        empty = {
            "distance_km": 0.0,
            "duration_hours": 0.0,
            "workout_count": 0,
            "workout_type": workout_type,
        }
        return [
            by_week.get(
                w.isoformat(), {"week_start": w.isoformat(), **empty}
            )
            for w in _date_range_spine(since, until)
        ]

    @staticmethod
    def _fill_weekly_strength_gaps(data: list[dict], year: int) -> list[dict]:
        by_week = {d["week_start"]: d for d in data}
        return [
            by_week.get(
                w.isoformat(), {"week_start": w.isoformat(), "count": 0}
            )
            for w in _week_spine(year)
        ]

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
        # Use rolling 12 months for the activity heatmap (GitHub-style)
        today = date.today()
        rolling_year = today.year if today.month > 1 else today.year - 1
        data = await self._analytics.training_log(athlete_id, rolling_year)
        if rolling_year != today.year:
            data += await self._analytics.training_log(athlete_id, today.year)
        else:
            # Also include last year's tail for the rolling window
            cutoff = (today - timedelta(days=365)).isoformat()
            prev_data = await self._analytics.training_log(athlete_id, rolling_year - 1)
            data = [d for d in prev_data if d["date"] >= cutoff] + data
        return data

    async def workouts_with_notes(self, athlete_id: str, year: int | None = None) -> list[dict]:
        year = year or current_year()
        return await self._analytics.workouts_with_notes(athlete_id, year)

    async def fitness_freshness_chart_data(
        self,
        athlete_id: str,
        days: int = 90,
        max_hr: int = 185,
    ) -> list[dict]:
        today = date.today()
        since = today - timedelta(days=days + CTL_SEED_DAYS)
        daily_efforts = await self._analytics.daily_effort(athlete_id, since, max_hr)
        return compute_fitness_freshness(daily_efforts, days)

    async def zone2_compliance(
        self,
        athlete_id: str,
        max_hr: int,
        aerobic_threshold_bpm: int | None,
        since: date,
        until: date,
    ) -> dict:
        """Compute % of running time with average HR in Zone 2."""
        bounds = compute_zone2_bounds(max_hr, aerobic_threshold_bpm)
        runs = await self._analytics.runs_with_hr(athlete_id, since, until)

        total_seconds = 0
        zone2_seconds = 0
        for run in runs:
            secs = run["moving_time_seconds"]
            hr = run["average_heartrate"]
            total_seconds += secs
            if bounds.lower <= hr < bounds.upper:
                zone2_seconds += secs

        pct = (zone2_seconds / total_seconds * 100) if total_seconds > 0 else 0
        return {
            "zone2_pct": round(pct, 1),
            "zone2_seconds": zone2_seconds,
            "total_seconds": total_seconds,
            "run_count": len(runs),
            "zone2_lower": round(bounds.lower),
            "zone2_upper": round(bounds.upper),
        }
