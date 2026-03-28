"""Weekly recap — closes the plan→train→reflect→adapt loop."""

import logging
from datetime import date, timedelta

from forma.application import llm
from forma.domain.fitness_freshness import classify_form, compute_fitness_freshness, CTL_SEED_DAYS
from forma.ports.athlete_repository import AthleteRepository
from forma.ports.plan_cache_repository import PlanCacheRepository
from forma.ports.workout_analytics_repository import WorkoutAnalyticsRepository
from forma.ports.workout_repository import WorkoutRepository

logger = logging.getLogger(__name__)

# In-memory cache: (athlete_id, week_start, session_count) → coach_note
_coach_note_cache: dict[tuple[str, str, int], str] = {}

_SYSTEM = (
    "You are a calm, experienced sports coach writing a weekly training recap. "
    "STRICT RULES: exactly 2 sentences. First sentence: what went well (reference specific sessions). "
    "Second sentence: one concrete recommendation for next week. "
    "Never guilt-trip missed sessions. No bullet points, no headers, no filler."
)


class WeeklyRecapService:
    def __init__(
        self,
        athlete_repo: AthleteRepository,
        workout_repo: WorkoutRepository,
        analytics_repo: WorkoutAnalyticsRepository,
        plan_cache: PlanCacheRepository,
    ):
        self._athlete_repo = athlete_repo
        self._workout_repo = workout_repo
        self._analytics_repo = analytics_repo
        self._plan_cache = plan_cache

    async def generate_recap(self, athlete_id: str) -> dict:
        today = date.today()
        dow = today.weekday()  # 0=Monday
        week_start = today - timedelta(days=dow)
        week_end = week_start + timedelta(days=6)
        prev_week_start = week_start - timedelta(days=7)

        athlete, this_week, prev_week, cached_plan = await self._fetch_data(
            athlete_id, prev_week_start, week_end,
        )

        adherence = self._compute_adherence(cached_plan, this_week, week_start, today)
        volume = self._compute_volume(this_week, prev_week)
        fitness_trend = await self._compute_fitness_trend(athlete_id, athlete, week_start, today)

        # Cache coach note by (athlete, week, session count) — only call LLM when data changes
        session_count = volume["current"]["sessions"]
        cache_key = (athlete_id, week_start.isoformat(), session_count)
        coach_note = _coach_note_cache.get(cache_key, "")
        if not coach_note and session_count > 0:
            coach_note = self._generate_coach_note(
                athlete, adherence, volume, fitness_trend, this_week, week_start,
            )
            if coach_note:
                _coach_note_cache[cache_key] = coach_note

        return {
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "day_of_week": dow,
            "adherence": adherence,
            "volume": volume,
            "fitness_trend": fitness_trend,
            "coach_note": coach_note,
        }

    async def _fetch_data(self, athlete_id, since, until):
        import asyncio
        athlete_task = self._athlete_repo.get(athlete_id)
        workouts_task = self._workout_repo.list_workouts_for_athlete(
            athlete_id, start_date=since, end_date=until + timedelta(days=1), limit=100,
        )
        plan_task = self._plan_cache.get(athlete_id)

        athlete, workouts, cached_plan = await asyncio.gather(
            athlete_task, workouts_task, plan_task,
        )

        week_start = until - timedelta(days=6)
        this_week = [w for w in workouts if w.start_time.date() >= week_start]
        prev_week = [w for w in workouts if w.start_time.date() < week_start]

        return athlete, this_week, prev_week, cached_plan

    def _compute_adherence(self, cached_plan, this_week, week_start, today) -> dict:
        # Always show Mon-Sun, merging plan + actual workouts
        plan_by_date = {}
        has_plan = False
        if cached_plan and cached_plan.days:
            has_plan = True
            for d in cached_plan.days:
                plan_by_date[d.day] = d

        workouts_by_date = {}
        for w in this_week:
            d = w.start_time.date()
            workouts_by_date.setdefault(d, []).append(w)

        completed = 0
        missed = 0
        swapped = 0
        total_planned = 0
        days = []

        for i in range(7):
            day = week_start + timedelta(days=i)
            planned = plan_by_date.get(day)
            actual = workouts_by_date.get(day, [])
            planned_type = planned.workout_type if planned else None
            is_future = day > today

            if planned and planned_type != "rest":
                total_planned += 1
                if actual:
                    actual_types = {w.workout_type.value for w in actual}
                    if planned_type in actual_types:
                        status = "completed"
                        completed += 1
                    else:
                        status = "swapped"
                        swapped += 1
                elif is_future:
                    status = "upcoming"
                else:
                    status = "missed"
                    missed += 1
            elif actual:
                # No plan or rest day, but worked out
                status = "extra"
            elif is_future:
                status = "upcoming"
            else:
                status = "rest"

            days.append({
                "date": day.isoformat(),
                "planned_type": planned_type or "rest",
                "status": status,
                "actual_type": actual[0].workout_type.value if actual else None,
            })

        return {
            "has_plan": has_plan,
            "completed": completed,
            "swapped": swapped,
            "missed": missed,
            "total_planned": total_planned,
            "days": days,
        }

    def _compute_volume(self, this_week, prev_week) -> dict:
        def summarize(workouts):
            sessions = len(workouts)
            minutes = sum(w.duration_minutes for w in workouts)
            km = sum(w.distance_km or 0 for w in workouts)
            return {"sessions": sessions, "minutes": round(minutes), "km": round(km, 1)}

        current = summarize(this_week)
        previous = summarize(prev_week)

        return {
            "current": current,
            "previous": previous,
        }

    async def _compute_fitness_trend(self, athlete_id, athlete, week_start, today) -> dict:
        max_hr = athlete.max_heartrate or (220 - athlete.age if athlete.age else 185)
        since = week_start - timedelta(days=CTL_SEED_DAYS + 7)
        efforts = await self._analytics_repo.daily_effort(athlete_id, since, max_hr)
        ff_data = compute_fitness_freshness(efforts, (today - week_start).days + CTL_SEED_DAYS + 7)

        week_start_str = week_start.isoformat()
        today_str = today.isoformat()

        start_entry = None
        end_entry = None
        for entry in ff_data:
            if entry["date"] == week_start_str:
                start_entry = entry
            if entry["date"] == today_str:
                end_entry = entry

        if not start_entry or not end_entry:
            return {}

        fitness_delta = end_entry["fitness"] - start_entry["fitness"]
        form_delta = end_entry["form"] - start_entry["form"]

        return {
            "fitness_now": end_entry["fitness"],
            "fitness_start": start_entry["fitness"],
            "fitness_delta": round(fitness_delta, 1),
            "form_now": end_entry["form"],
            "form_start": start_entry["form"],
            "form_delta": round(form_delta, 1),
            "status": classify_form(end_entry["form"], end_entry["fitness"], end_entry["fatigue"]),
        }

    def _generate_coach_note(self, athlete, adherence, volume, fitness_trend, this_week, week_start) -> str:
        try:
            return self._call_llm_for_note(athlete, adherence, volume, fitness_trend, this_week, week_start)
        except Exception:
            logger.exception("failed to generate weekly recap coach note")
            return ""

    def _call_llm_for_note(self, athlete, adherence, volume, fitness_trend, this_week, week_start) -> str:
        prompt = self._build_recap_prompt(athlete, adherence, volume, fitness_trend, this_week, week_start)
        text = llm.generate(system=_SYSTEM, prompt=prompt, service="weekly_recap", athlete_id=athlete.id)
        return text.strip().strip('"')

    def _build_recap_prompt(self, athlete, adherence, volume, fitness_trend, this_week, week_start) -> str:
        today = date.today()
        dow = today.weekday()
        day_name = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][dow]

        # Adherence block
        if adherence.get("has_plan"):
            adherence_block = (
                f"Plan adherence: {adherence['completed']}/{adherence['total_planned']} completed, "
                f"{adherence['swapped']} swapped, {adherence['missed']} missed"
            )
            day_details = []
            for d in adherence.get("days", []):
                if d["planned_type"] == "rest":
                    continue
                status_emoji = {"completed": "done", "swapped": "swapped", "missed": "missed", "upcoming": "upcoming"}
                detail = f"  - {d['date']}: planned {d['planned_type']}, {status_emoji.get(d['status'], d['status'])}"
                if d.get("actual_type"):
                    detail += f" (did {d['actual_type']})"
                day_details.append(detail)
            adherence_block += "\n" + "\n".join(day_details)
        else:
            adherence_block = "No training plan was active this week."

        # Volume block
        curr = volume["current"]
        prev = volume["previous"]
        volume_block = (
            f"This week so far: {curr['sessions']} sessions, {curr['minutes']} min, {curr['km']} km running\n"
            f"Last week total: {prev['sessions']} sessions, {prev['minutes']} min, {prev['km']} km running"
        )

        # Fitness block
        fitness_block = "Fitness data not available."
        if fitness_trend:
            fitness_block = (
                f"Fitness (CTL): {fitness_trend['fitness_start']} → {fitness_trend['fitness_now']} "
                f"({'+' if fitness_trend['fitness_delta'] >= 0 else ''}{fitness_trend['fitness_delta']})\n"
                f"Form (TSB): {fitness_trend['form_start']} → {fitness_trend['form_now']} "
                f"({'+' if fitness_trend['form_delta'] >= 0 else ''}{fitness_trend['form_delta']})\n"
                f"Current state: {fitness_trend['status']}"
            )

        # Workout details
        workout_lines = []
        for w in sorted(this_week, key=lambda x: x.start_time):
            line = f"  - {w.start_time.strftime('%a')} {w.workout_type.value} {w.duration_minutes:.0f}min"
            if w.distance_km:
                line += f" {w.distance_km:.1f}km"
            if w.perceived_effort:
                line += f" (felt {w.perceived_effort.value})"
            workout_lines.append(line)
        workouts_block = "\n".join(workout_lines) or "  (no workouts recorded)"

        # Goal context
        goal_block = ""
        if athlete.primary_goal:
            g = athlete.primary_goal
            goal_block = f"\nGoal: {g.description}"
            if g.target_date:
                days_left = (g.target_date - today).days
                goal_block += f" ({days_left} days away)"
            upcoming = [m for m in (g.milestones or []) if m.date >= today]
            if upcoming:
                upcoming.sort(key=lambda m: m.date)
                nm = upcoming[0]
                goal_block += f"\nNext milestone: {nm.description} by {nm.date.strftime('%-d %b')}"

        return f"""Today is {day_name} {today.strftime('%-d %B %Y')}. Write a brief weekly recap for this athlete.

{adherence_block}

VOLUME:
{volume_block}

FITNESS TREND:
{fitness_block}

SESSIONS THIS WEEK:
{workouts_block}
{goal_block}

Write 2-3 sentences: what went well, what could improve, and one recommendation for next week. Be specific — reference actual sessions and numbers."""
