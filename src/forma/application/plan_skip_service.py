"""Plan skip service — 'Not today' day swap."""

from datetime import date

from forma.domain.plan_swap import find_swap_target, swap_days
from forma.ports.athlete_repository import AthleteRepository
from forma.ports.plan_cache_repository import PlanCacheRepository


class PlanSkipService:
    def __init__(
        self,
        plan_cache: PlanCacheRepository,
        athlete_repo: AthleteRepository,
    ):
        self._plan_cache = plan_cache
        self._athlete_repo = athlete_repo

    async def skip_day(self, athlete_id: str, skip_date: date) -> dict:
        cached = await self._plan_cache.get(athlete_id)
        if not cached:
            return {"swapped_with": None, "days": []}

        athlete = await self._athlete_repo.get(athlete_id)
        constraints = athlete.schedule_template if athlete else []

        target = find_swap_target(cached.days, skip_date, constraints)
        if not target:
            return {
                "swapped_with": None,
                "days": [self._day_dict(d) for d in cached.days],
            }

        new_days = swap_days(cached.days, skip_date, target)
        await self._plan_cache.save_days(athlete_id, new_days)

        return {
            "swapped_with": target.isoformat(),
            "days": [self._day_dict(d) for d in new_days],
        }

    def _day_dict(self, d) -> dict:
        return {
            "date": d.day.isoformat(),
            "workout_type": d.workout_type,
            "intensity": d.intensity,
            "duration_minutes": d.duration_minutes,
            "description": d.description,
            "exercises": d.exercises,
        }
