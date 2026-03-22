"""Athlete profile management service."""

import json
from dataclasses import dataclass
from datetime import date

from forma.application.llm import check_ai_access, generate as llm_generate

from forma.domain.athlete import Athlete, Goal, ScheduleTemplateSlot
from forma.ports.athlete_repository import AthleteRepository
from forma.ports.workout_repository import WorkoutRepository


@dataclass
class GoalAdvice:
    """AI-generated advice for the athlete's primary goal."""

    summary: str
    training_tips: list[str]
    weekly_focus: str


class AthleteProfileService:
    """Manages athlete profile, goals, and AI-powered goal advice."""

    def __init__(
        self,
        athlete_repo: AthleteRepository,
        workout_repo: WorkoutRepository,
    ) -> None:
        self._athletes = athlete_repo
        self._workouts = workout_repo

    async def get_profile(self, athlete_id: str) -> Athlete | None:
        return await self._athletes.get(athlete_id)

    async def update_profile(self, athlete_id: str, updates: dict) -> Athlete:
        athlete = await self._athletes.get(athlete_id)
        if athlete is None:
            raise ValueError(f"Athlete {athlete_id} not found")
        updated = athlete.model_copy(update=updates)
        await self._athletes.save(updated)
        return updated

    async def set_primary_goal(self, athlete_id: str, goal: Goal) -> Athlete:
        athlete = await self._athletes.get(athlete_id)
        if athlete is None:
            raise ValueError(f"Athlete {athlete_id} not found")
        updated = athlete.with_primary_goal(goal)
        await self._athletes.save(updated)
        return updated

    async def remove_primary_goal(self, athlete_id: str) -> Athlete:
        athlete = await self._athletes.get(athlete_id)
        if athlete is None:
            raise ValueError(f"Athlete {athlete_id} not found")
        updated = athlete.without_primary_goal()
        await self._athletes.save(updated)
        return updated

    async def add_schedule_slot(self, athlete_id: str, slot: ScheduleTemplateSlot) -> Athlete:
        athlete = await self._athletes.get(athlete_id)
        if athlete is None:
            raise ValueError(f"Athlete {athlete_id} not found")
        updated = athlete.with_schedule_slot(slot)
        await self._athletes.save(updated)
        return updated

    async def remove_schedule_slot(self, athlete_id: str, slot_index: int) -> Athlete:
        athlete = await self._athletes.get(athlete_id)
        if athlete is None:
            raise ValueError(f"Athlete {athlete_id} not found")
        updated = athlete.without_schedule_slot(slot_index)
        await self._athletes.save(updated)
        return updated

    async def get_goal_advice(self, athlete_id: str) -> GoalAdvice:
        await check_ai_access(athlete_id)
        athlete = await self._athletes.get(athlete_id)
        if athlete is None:
            raise ValueError(f"Athlete {athlete_id} not found")
        if not athlete.primary_goal:
            raise ValueError("No primary goal set")

        recent_workouts = await self._workouts.get_recent(athlete_id, count=28)
        prompt = self._build_advice_prompt(athlete, recent_workouts)
        text = llm_generate(prompt=prompt, service="profile-advice", athlete_id=athlete_id)
        return self._parse_advice_response(text)

    def _build_advice_prompt(self, athlete: Athlete, recent_workouts: list) -> str:
        goal = athlete.primary_goal
        age_str = f"{athlete.age} years old" if athlete.age else "age unknown"
        weight_str = f"{athlete.weight_kg} kg" if athlete.weight_kg else "weight unknown"

        workouts_block = "\n".join(
            f"- {w.start_time.strftime('%Y-%m-%d')} {w.workout_type.value} "
            + (f"{w.distance_km:.1f}km " if w.distance_km else "")
            + f"{w.duration_minutes:.0f}min"
            + (f" pace {w.pace_formatted()}" if w.pace_formatted() else "")
            + (f" HR {w.average_heartrate:.0f}" if w.average_heartrate else "")
            for w in recent_workouts
        )

        target_str = ""
        if goal.target_date:
            days_left = (goal.target_date - date.today()).days
            target_str = f"\nTarget date: {goal.target_date} ({days_left} days away)"
        if goal.target_value:
            target_str += f"\nTarget value: {goal.target_value}"

        history_block = ""
        if athlete.goal_history:
            lines = [
                f"  - [{e.set_at.strftime('%Y-%m-%d')} → {e.retired_at.strftime('%Y-%m-%d')}]"
                f" {e.goal_type.value}: {e.description}"
                + (f" (target: {e.target_value})" if e.target_value else "")
                for e in sorted(athlete.goal_history, key=lambda e: e.set_at)
            ]
            history_block = "\nPrevious goals (most recent last):\n" + "\n".join(lines)

        return f"""You are a personal running and fitness coach giving tailored training advice.

Athlete profile:
- Age: {age_str}
- Weight: {weight_str}
- Max hours/week: {athlete.max_hours_per_week or 'not set'}

Primary goal (current):
- Type: {goal.goal_type.value}
- Description: {goal.description}{target_str}
- Set on: {goal.set_at.strftime('%Y-%m-%d')}{history_block}

Recent workouts (last 4 weeks):
{workouts_block or 'No recent workouts'}

Based on this athlete's profile, goal, and recent training, respond with a JSON object:
{{
  "summary": "2-3 sentence interpretation of their goal and current fitness relative to it",
  "training_tips": ["specific actionable tip 1", "tip 2", "tip 3", "tip 4"],
  "weekly_focus": "One sentence on what to focus on this week specifically"
}}

Respond with only the JSON object, no other text."""

    def _parse_advice_response(self, text: str) -> GoalAdvice:
        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(cleaned)
            return GoalAdvice(
                summary=data.get("summary", ""),
                training_tips=data.get("training_tips", []),
                weekly_focus=data.get("weekly_focus", ""),
            )
        except json.JSONDecodeError:
            return GoalAdvice(
                summary=text,
                training_tips=[],
                weekly_focus="",
            )
