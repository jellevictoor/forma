"""Strands-based AI fitness coach adapter."""

from strands import Agent
from strands.models.ollama import OllamaModel

from fitness_coach.domain.athlete import Athlete
from fitness_coach.domain.schedule import Schedule
from fitness_coach.domain.workout import Workout
from fitness_coach.ports.coach import Coach, CoachContext, CoachResponse


SYSTEM_PROMPT = """You are a personal fitness coach. You are practical, concrete, and never overcomplicate things.

## Your communication style:
- Be direct and actionable
- Use clear tables and checklists when helpful
- Explain the "why" briefly, but focus on the "what to do"
- Use structured formatting (bullets, tables) for clarity
- Be encouraging but honest - no fake praise
- Focus on sustainability over intensity

## Key principles you follow:
- Quality > volume for home workouts
- Never train to failure
- Easy runs should feel "boring" - conversational pace
- Core work = anti-movement (stability)
- Consistency beats hero workouts
- Recovery is part of training

## What you know about the athlete:
{athlete_context}

## Current training schedule:
{schedule_context}

## Recent workout history:
{workout_context}

Based on this context, help the athlete with their question. Be specific to their situation.
If they share workout data, analyze it concretely. If they ask about adjustments, be practical.
"""


def _format_athlete_context(athlete: Athlete) -> str:
    lines = [
        f"- Name: {athlete.name}",
        f"- Age: {athlete.age or 'unknown'}",
        f"- Weight: {athlete.weight_kg or 'unknown'} kg",
    ]

    if athlete.goals:
        goals_str = ", ".join(g.description for g in athlete.goals)
        lines.append(f"- Goals: {goals_str}")

    if athlete.active_injuries:
        injuries_str = ", ".join(i.description for i in athlete.active_injuries)
        lines.append(f"- Current limitations: {injuries_str}")

    if athlete.max_hours_per_week:
        lines.append(f"- Max training hours/week: {athlete.max_hours_per_week}")

    if athlete.notes:
        lines.append(f"- Notes: {athlete.notes}")

    return "\n".join(lines)


def _format_schedule_context(schedule: Schedule | None) -> str:
    if not schedule:
        return "No active schedule set."

    lines = [
        f"- Schedule: {schedule.name}",
        f"- Current week: {schedule.current_week}",
        f"- Phase: {schedule.current_phase.value}",
    ]

    if schedule.target_event:
        lines.append(f"- Target event: {schedule.target_event}")

    today_workout = schedule.get_today_workout()
    if today_workout:
        lines.append(f"- Today's workout: {today_workout.workout_type.value} - {today_workout.description}")

    return "\n".join(lines)


def _format_workout_context(workouts: list[Workout] | None) -> str:
    if not workouts:
        return "No recent workouts recorded."

    lines = ["Recent workouts:"]
    for w in workouts[:5]:
        pace_str = f" @ {w.pace_formatted()}" if w.pace_formatted() else ""
        hr_str = f", HR {w.average_heartrate:.0f}" if w.average_heartrate else ""
        duration = f"{w.duration_minutes:.0f}min"

        line = f"- {w.start_time.strftime('%a %d %b')}: {w.workout_type.value} {duration}{pace_str}{hr_str}"
        if w.private_note:
            line += f" | Note: {w.private_note[:50]}"
        lines.append(line)

    return "\n".join(lines)


class StrandsCoach(Coach):
    """AI fitness coach using Strands agents."""

    def __init__(self, model: str = "llama3.1:8b", host: str = "http://localhost:11434"):
        self.model = OllamaModel(
            model_id=model,
            host=host,
        )

    def _build_system_prompt(self, context: CoachContext) -> str:
        return SYSTEM_PROMPT.format(
            athlete_context=_format_athlete_context(context.athlete),
            schedule_context=_format_schedule_context(context.schedule),
            workout_context=_format_workout_context(context.recent_workouts),
        )

    def _create_agent(self, context: CoachContext) -> Agent:
        return Agent(
            model=self.model,
            system_prompt=self._build_system_prompt(context),
        )

    async def chat(self, message: str, context: CoachContext) -> CoachResponse:
        agent = self._create_agent(context)
        response = agent(message)
        return CoachResponse(message=str(response))

    async def analyze_workout(self, workout: Workout, context: CoachContext) -> CoachResponse:
        distance_str = f"{workout.distance_km:.2f} km" if workout.distance_km else "N/A"
        prompt = f"""Analyze this workout:

Type: {workout.workout_type.value}
Duration: {workout.duration_minutes:.0f} minutes
Distance: {distance_str}
Pace: {workout.pace_formatted() or "N/A"}
Average HR: {workout.average_heartrate or "N/A"} bpm
Max HR: {workout.max_heartrate or "N/A"} bpm
Athlete's note: {workout.private_note or "None"}

Provide:
1. A quick assessment (was this the right intensity?)
2. Any observations about the data
3. One small tip for next time (if relevant)

Keep it brief and practical."""

        agent = self._create_agent(context)
        response = agent(prompt)
        return CoachResponse(message=str(response))

    async def get_daily_briefing(self, context: CoachContext) -> CoachResponse:
        prompt = """Give me today's briefing:

1. What's on the schedule today?
2. Any quick reminders based on recent workouts?
3. One focus point for today

Keep it short - this should take 30 seconds to read."""

        agent = self._create_agent(context)
        response = agent(prompt)
        return CoachResponse(message=str(response))

    async def suggest_schedule_adjustment(
        self,
        reason: str,
        context: CoachContext,
    ) -> CoachResponse:
        prompt = f"""I need to adjust my schedule because: {reason}

Based on my current schedule and recent workouts, suggest:
1. What to change this week
2. How to make up for it (if needed)
3. Whether it's actually fine to skip/modify

Be practical - sometimes the right answer is "just skip it"."""

        agent = self._create_agent(context)
        response = agent(prompt)
        return CoachResponse(message=str(response))
