"""Plan adherence — compare planned workouts with actual activity."""

from datetime import date, timedelta

from forma.ports.plan_cache_repository import PlanCacheRepository
from forma.ports.workout_repository import WorkoutRepository


class PlanAdherenceService:
    def __init__(
        self,
        plan_cache: PlanCacheRepository,
        workout_repo: WorkoutRepository,
    ):
        self._plan_cache = plan_cache
        self._workout_repo = workout_repo

    async def get_adherence(self, athlete_id: str) -> list[dict]:
        cached = await self._plan_cache.get(athlete_id)
        if not cached:
            return []

        plan_dates = [d.day for d in cached.days]
        if not plan_dates:
            return []

        start = min(plan_dates)
        end = max(plan_dates)
        workouts = await self._workout_repo.list_workouts_for_athlete(
            athlete_id, start_date=start, end_date=end + timedelta(days=1), limit=100,
        )

        workouts_by_date: dict[date, list] = {}
        for w in workouts:
            d = w.start_time.date()
            workouts_by_date.setdefault(d, []).append(w)

        today = date.today()
        result = []
        for planned in cached.days:
            actual = workouts_by_date.get(planned.day, [])
            status = self._compute_status(planned, actual, today)
            entry = {
                "date": planned.day.isoformat(),
                "planned_type": planned.workout_type,
                "status": status,
            }
            if actual:
                entry["actual_type"] = actual[0].workout_type.value
                entry["actual_duration"] = actual[0].duration_minutes
            result.append(entry)

        return result

    def _compute_status(self, planned, actual, today: date) -> str:
        if planned.workout_type == "rest":
            return "completed" if not actual else "swapped"
        if planned.day >= today:
            return "upcoming"
        if not actual:
            return "missed"
        actual_types = {w.workout_type.value for w in actual}
        if planned.workout_type in actual_types:
            return "completed"
        return "swapped"
