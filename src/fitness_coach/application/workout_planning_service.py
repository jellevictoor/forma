"""Workout planning service — generates a 7-day rolling plan using Gemini."""

import json
from datetime import date, datetime, timedelta, timezone

from google import genai

from fitness_coach.domain.fitness_freshness import CTL_SEED_DAYS, compute_fitness_freshness
from fitness_coach.ports.athlete_repository import AthleteRepository
from fitness_coach.ports.plan_cache_repository import (
    CachedWeeklyPlan,
    PlannedDay,
    PlanCacheRepository,
    WeeklyPlan,
)
from fitness_coach.ports.workout_analytics_repository import WorkoutAnalyticsRepository
from fitness_coach.ports.workout_repository import WorkoutRepository

PLAN_MODEL = "models/gemini-2.5-flash"

_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


class WorkoutPlanningService:
    """Generates a 7-day rolling training plan using Gemini."""

    def __init__(
        self,
        athlete_repo: AthleteRepository,
        workout_repo: WorkoutRepository,
        analytics_repo: WorkoutAnalyticsRepository,
        gemini_api_key: str,
        plan_cache_repo: PlanCacheRepository,
    ) -> None:
        self._athletes = athlete_repo
        self._workouts = workout_repo
        self._analytics = analytics_repo
        self._client = genai.Client(api_key=gemini_api_key)
        self._cache = plan_cache_repo

    async def get_cached(self, athlete_id: str) -> CachedWeeklyPlan | None:
        """Return cached plan with staleness flag set."""
        cached = await self._cache.get(athlete_id)
        if cached is None:
            return None
        recent = await self._workouts.get_recent(athlete_id, count=1)
        latest_at = recent[0].start_time if recent else None
        cached.is_stale = (
            latest_at is not None
            and cached.latest_activity_at is not None
            and latest_at > cached.latest_activity_at
        )
        return cached

    async def generate_and_cache(self, athlete_id: str) -> CachedWeeklyPlan:
        """Generate via Gemini, persist to cache, and return."""
        plan = await self._generate(athlete_id)
        if not plan.days:
            raise ValueError("Gemini returned an empty plan — not caching")
        recent = await self._workouts.get_recent(athlete_id, count=1)
        latest_activity_at = recent[0].start_time if recent else None
        await self._cache.save(athlete_id, plan, latest_activity_at)
        return CachedWeeklyPlan(
            days=plan.days,
            rationale=plan.rationale,
            generated_at=plan.generated_at,
            latest_activity_at=latest_activity_at,
            is_stale=False,
        )

    async def get_exercises_for_day(
        self, athlete_id: str, day: date, workout_type: str, description: str = ""
    ) -> dict[str, list[str]]:
        """Return cached exercises for a day, or generate and cache them if missing."""
        cached = await self._cache.get(athlete_id)
        if cached:
            for planned_day in cached.days:
                if planned_day.day == day and planned_day.exercises:
                    return planned_day.exercises
        return await self._generate_and_cache_exercises(athlete_id, day, workout_type, description)

    async def refresh_exercises_for_day(
        self, athlete_id: str, day: date, workout_type: str, description: str = ""
    ) -> dict[str, list[str]]:
        """Always regenerate exercises via Gemini and update the cache."""
        return await self._generate_and_cache_exercises(athlete_id, day, workout_type, description)

    async def _generate_and_cache_exercises(
        self, athlete_id: str, day: date, workout_type: str, description: str
    ) -> dict[str, list[str]]:
        athlete = await self._athletes.get(athlete_id)
        since = date.today() - timedelta(days=60)
        recent_workouts = await self._workouts.list_workouts_for_athlete(
            athlete_id, start_date=since, limit=50
        )
        workouts_with_notes = [w for w in recent_workouts if w.private_note]
        prompt = self._build_exercises_prompt(athlete, day, workout_type, description, workouts_with_notes)
        exercises = self._call_gemini_for_exercises(prompt)
        await self._cache.update_day_exercises(athlete_id, day, exercises)
        return exercises

    async def _generate(self, athlete_id: str) -> WeeklyPlan:
        athlete = await self._athletes.get(athlete_id)
        if athlete is None:
            raise ValueError(f"Athlete {athlete_id} not found")
        recent_workouts = await self._workouts.get_recent(athlete_id, count=20)
        ff = await self._current_fitness_freshness(athlete_id)
        completed_dates = await self._completed_dates_in_window(athlete_id)
        prompt = self._build_plan_prompt(athlete, recent_workouts, ff, completed_dates)
        return self._call_gemini_for_plan(prompt)

    async def _completed_dates_in_window(self, athlete_id: str) -> set[date]:
        today = date.today()
        window_end = today + timedelta(days=6)
        window_workouts = await self._workouts.list_workouts_for_athlete(
            athlete_id, start_date=today, end_date=window_end, limit=7
        )
        return {w.start_time.date() for w in window_workouts}

    async def _current_fitness_freshness(self, athlete_id: str) -> dict:
        since = date.today() - timedelta(days=CTL_SEED_DAYS + 7)
        daily_efforts = await self._analytics.daily_effort(athlete_id, since)
        ff = compute_fitness_freshness(daily_efforts, display_days=1)
        return ff[-1] if ff else {"fitness": 0.0, "fatigue": 0.0, "form": 0.0}

    def _build_plan_prompt(self, athlete, recent_workouts: list, ff: dict, completed_dates: set) -> str:
        today = date.today()
        next_7_days = [d for d in (today + timedelta(days=i) for i in range(7)) if d not in completed_dates]

        slot_lines = [
            f"  - {_DAY_NAMES[s.day_of_week]}: {s.workout_type.value}"
            for s in athlete.schedule_template
        ]
        schedule_block = "\n".join(slot_lines) if slot_lines else "  (no fixed schedule defined)"

        def fmt_workout(w) -> str:
            line = f"  - {w.start_time.strftime('%a %b %d')} {w.workout_type.value} {w.duration_minutes:.0f}min"
            if w.distance_km:
                line += f" {w.distance_km:.1f}km"
            if w.pace_formatted():
                line += f" pace {w.pace_formatted()}"
            if w.average_heartrate:
                line += f" HR {w.average_heartrate:.0f}"
            if w.private_note:
                line += f" [note: {w.private_note[:80]}]"
            return line

        recent_block = "\n".join(fmt_workout(w) for w in recent_workouts) or "  None"

        goal_lines = [f"  - {g.goal_type.value}: {g.description}" for g in athlete.goals]
        goals_block = "\n".join(goal_lines) or "  (no goals set)"

        injury_lines = [f"  - {i.affected_area}: {i.description}" for i in athlete.active_injuries]
        injuries_block = "\n".join(injury_lines) or "  None"

        form = ff["form"]
        if form > 5:
            form_context = "positive — athlete is fresh, can push harder"
        elif form < -10:
            form_context = "negative — fatigue accumulated, prioritise recovery"
        else:
            form_context = "neutral — balanced training load"

        max_minutes = (athlete.max_hours_per_week or 10) * 60

        plan_window = "\n".join(
            f"  - {d.strftime('%Y-%m-%d')} ({_DAY_NAMES[d.weekday()]})"
            for d in next_7_days
        )

        return f"""You are a personal fitness coach. Generate a training plan for the open days listed below. Days not listed already have a completed workout and must be skipped.

PLAN WINDOW (open days only):
{plan_window}

FIXED SCHEDULE CONSTRAINTS (you MUST honour these on the specified days):
{schedule_block}

RECENT TRAINING (last 20 sessions):
{recent_block}

ATHLETE PROFILE:
- Max hours per week: {athlete.max_hours_per_week or 'not set'}
- Goals:
{goals_block}
- Active injuries or limitations:
{injuries_block}
- Notes: {athlete.notes}

CURRENT FITNESS STATE:
- Fitness (chronic load): {ff['fitness']:.0f}
- Fatigue (acute load): {ff['fatigue']:.0f}
- Form: {form:.0f} — {form_context}

RULES:
- Honour the fixed schedule constraints exactly (sport and day).
- For unconstrained days, choose rest or optional cross-training based on load and form.
- Adjust intensity based on form score: high fatigue means lower intensity.
- Total weekly duration must not exceed {max_minutes:.0f} minutes.
- Intensity values: "recovery", "easy", "moderate", "tempo", "threshold".
- Workout type values: "run", "strength", "climbing", "rest", "walk", "cross_training".

Respond with a JSON object:
{{
  "rationale": "2-3 sentences explaining the weekly plan logic",
  "days": [
    {{
      "date": "YYYY-MM-DD",
      "workout_type": "run|strength|climbing|rest|walk|cross_training",
      "intensity": "recovery|easy|moderate|tempo|threshold",
      "duration_minutes": 45,
      "description": "One sentence describing what to do and why"
    }}
  ]
}}

Include exactly 7 entries in "days", one for each date in the plan window.
Respond with only the JSON, no other text."""

    def _build_exercises_prompt(
        self, athlete, day: date, workout_type: str, description: str, workouts_with_notes: list
    ) -> str:
        notes_block = "\n".join(
            f"  [{w.start_time.strftime('%b %d')} {w.workout_type.value}] {w.private_note}"
            for w in workouts_with_notes
        ) or "  (no exercise notes found)"

        session_context = f"{workout_type} — {description}" if description else workout_type

        return f"""You are a personal fitness coach. The athlete has the following session planned for {day.strftime('%A %B %d, %Y')}:

SESSION: {session_context}

RECENT WORKOUT NOTES (exercises documented in previous sessions):
{notes_block}

ATHLETE NOTES:
{athlete.notes or '  (none)'}

Based on the planned session description and the athlete's documented exercises, suggest a concrete workout that matches the session intent.
Reference specific circuits or exercises from the notes where relevant.

Respond with a JSON object with three sections:
{{
  "warmup": ["exercise 1", "exercise 2"],
  "main": ["exercise 1", "exercise 2", "exercise 3"],
  "cooldown": ["exercise 1", "exercise 2"]
}}

Each item is a concise exercise string (e.g. "3×10 goblet squat @ 24\u202fkg", "5\u202fmin easy jog").
Respond with only the JSON object, no other text."""

    def _call_gemini_for_plan(self, prompt: str) -> WeeklyPlan:
        response = self._client.models.generate_content(model=PLAN_MODEL, contents=prompt)
        return self._parse_plan_response(response.text)

    def _call_gemini_for_exercises(self, prompt: str) -> dict[str, list[str]]:
        response = self._client.models.generate_content(model=PLAN_MODEL, contents=prompt)
        return self._parse_exercises_response(response.text)

    def _parse_plan_response(self, text: str) -> WeeklyPlan:
        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(cleaned)
            days = [
                PlannedDay(
                    day=date.fromisoformat(d["date"]),
                    workout_type=d.get("workout_type", "rest"),
                    intensity=d.get("intensity", "easy"),
                    duration_minutes=int(d.get("duration_minutes", 0)),
                    description=d.get("description", ""),
                )
                for d in data.get("days", [])
            ]
            return WeeklyPlan(
                days=days,
                rationale=data.get("rationale", ""),
                generated_at=datetime.now(tz=timezone.utc),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            return WeeklyPlan(
                days=[],
                rationale=text,
                generated_at=datetime.now(tz=timezone.utc),
            )

    def _parse_exercises_response(self, text: str) -> dict[str, list[str]]:
        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            result = json.loads(cleaned)
            if not isinstance(result, dict):
                return {"main": [text]}
            return {
                "warmup": result.get("warmup", []),
                "main": result.get("main", []),
                "cooldown": result.get("cooldown", []),
            }
        except json.JSONDecodeError:
            return {"main": [text]}
