"""Training alerts — pure computation on existing analytics data."""

from datetime import date, timedelta

from pydantic import BaseModel

from forma.domain.workout import PerceivedEffort
from forma.ports.athlete_repository import AthleteRepository
from forma.ports.plan_cache_repository import PlanCacheRepository
from forma.ports.workout_analytics_repository import WorkoutAnalyticsRepository
from forma.ports.workout_repository import WorkoutRepository

HARD_EFFORTS = {PerceivedEffort.HARD, PerceivedEffort.VERY_HARD, PerceivedEffort.MAXIMUM}
VOLUME_SPIKE_THRESHOLD = 1.25
CONSECUTIVE_HARD_DAYS_THRESHOLD = 3
CONSECUTIVE_TRAINING_DAYS_THRESHOLD = 7
GOAL_DRIFT_MISS_THRESHOLD = 2


class TrainingAlert(BaseModel):
    alert_type: str
    message: str
    severity: str  # "info", "warning", "critical"


class TrainingAlertsService:
    def __init__(
        self,
        workout_repo: WorkoutRepository,
        analytics_repo: WorkoutAnalyticsRepository,
        plan_cache: PlanCacheRepository | None = None,
        athlete_repo: AthleteRepository | None = None,
    ):
        self._workouts = workout_repo
        self._analytics = analytics_repo
        self._plan_cache = plan_cache
        self._athlete_repo = athlete_repo

    async def check(self, athlete_id: str) -> list[TrainingAlert]:
        alerts: list[TrainingAlert] = []

        today = date.today()
        workouts = await self._workouts.list_workouts_for_athlete(
            athlete_id, start_date=today - timedelta(days=14), limit=100,
        )

        self._check_no_rest_day(workouts, alerts)
        self._check_consecutive_hard_days(workouts, alerts)
        await self._check_volume_spike(athlete_id, alerts)
        await self._check_goal_drift(athlete_id, workouts, alerts)

        return alerts

    def _check_no_rest_day(self, workouts, alerts: list[TrainingAlert]) -> None:
        if not workouts:
            return
        training_dates = {w.start_time.date() for w in workouts}
        today = date.today()
        consecutive = 0
        for i in range(14):
            d = today - timedelta(days=i)
            if d in training_dates:
                consecutive += 1
                if consecutive >= CONSECUTIVE_TRAINING_DAYS_THRESHOLD:
                    alerts.append(TrainingAlert(
                        alert_type="no_rest_day",
                        message=f"{consecutive} days without rest — consider a recovery day",
                        severity="warning",
                    ))
                    return
            else:
                consecutive = 0

    def _check_consecutive_hard_days(self, workouts, alerts: list[TrainingAlert]) -> None:
        rated = [w for w in workouts if w.perceived_effort is not None]
        if not rated:
            return
        by_date = {}
        for w in rated:
            d = w.start_time.date()
            if d not in by_date or w.perceived_effort in HARD_EFFORTS:
                by_date[d] = w.perceived_effort
        today = date.today()
        consecutive = 0
        for i in range(14):
            d = today - timedelta(days=i)
            effort = by_date.get(d)
            if effort in HARD_EFFORTS:
                consecutive += 1
                if consecutive >= CONSECUTIVE_HARD_DAYS_THRESHOLD:
                    alerts.append(TrainingAlert(
                        alert_type="consecutive_hard_days",
                        message=f"{consecutive} hard sessions in a row — back off to avoid overreaching",
                        severity="warning",
                    ))
                    return
            else:
                consecutive = 0

    async def _check_volume_spike(self, athlete_id: str, alerts: list[TrainingAlert]) -> None:
        today = date.today()
        since = today - timedelta(weeks=5)
        volumes = await self._analytics.weekly_volume_for_range(athlete_id, since, today)
        if len(volumes) < 3:
            return
        sorted_vols = sorted(volumes, key=lambda v: v.week_start)
        current = sorted_vols[-1]
        baseline_vols = sorted_vols[:-1]
        avg_duration = sum(v.total_duration_seconds for v in baseline_vols) / len(baseline_vols)
        if avg_duration == 0:
            return
        ratio = current.total_duration_seconds / avg_duration
        if ratio >= VOLUME_SPIKE_THRESHOLD:
            pct = int((ratio - 1) * 100)
            alerts.append(TrainingAlert(
                alert_type="volume_spike",
                message=f"This week's volume is {pct}% above your recent average — watch for fatigue",
                severity="warning",
            ))

    async def _check_goal_drift(
        self, athlete_id: str, workouts, alerts: list[TrainingAlert],
    ) -> None:
        if not self._plan_cache or not self._athlete_repo:
            return
        cached = await self._plan_cache.get(athlete_id)
        if not cached:
            return
        athlete = await self._athlete_repo.get(athlete_id)
        if not athlete or not athlete.primary_goal:
            return

        today = date.today()
        past_days = [d for d in cached.days if d.day < today and d.workout_type != "rest"]
        if not past_days:
            return

        workout_dates = {w.start_time.date() for w in workouts}
        missed = sum(1 for d in past_days if d.day not in workout_dates)

        if missed < GOAL_DRIFT_MISS_THRESHOLD:
            return

        goal = athlete.primary_goal
        milestone_msg = ""
        upcoming = [m for m in goal.milestones if m.date >= today]
        if upcoming:
            nearest = min(upcoming, key=lambda m: m.date)
            days_left = (nearest.date - today).days
            if days_left <= 21:
                milestone_msg = f" — next milestone in {days_left} days"

        alerts.append(TrainingAlert(
            alert_type="goal_drift",
            message=f"{missed} planned sessions missed this week{milestone_msg}",
            severity="warning",
        ))
