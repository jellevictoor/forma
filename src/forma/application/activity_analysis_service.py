"""Activity analysis service — AI-powered per-workout analysis using Gemini."""

import json
from datetime import date, datetime, timedelta, timezone

from google import genai

from forma.domain.fitness_freshness import CTL_SEED_DAYS, compute_fitness_freshness
from forma.domain.workout import Workout
from forma.ports.activity_analysis_repository import (
    ActivityAnalysis,
    ActivityAnalysisRepository,
    CachedActivityAnalysis,
)
from forma.ports.athlete_repository import AthleteRepository
from forma.ports.chat_repository import ChatMessage, ChatRepository
from forma.ports.workout_analytics_repository import WorkoutAnalyticsRepository
from forma.ports.workout_repository import WorkoutRepository

ANALYSIS_MODEL = "models/gemini-2.5-flash"


class ActivityAnalysisService:
    """Generates per-workout AI analysis and conversation using Gemini."""

    def __init__(
        self,
        workout_repo: WorkoutRepository,
        analytics_repo: WorkoutAnalyticsRepository,
        athlete_repo: AthleteRepository,
        gemini_api_key: str,
        cache_repo: ActivityAnalysisRepository,
        chat_repo: ChatRepository,
    ) -> None:
        self._workouts = workout_repo
        self._analytics = analytics_repo
        self._athletes = athlete_repo
        self._client = genai.Client(api_key=gemini_api_key)
        self._cache = cache_repo
        self._chat = chat_repo

    async def get_cached(self, workout_id: str) -> CachedActivityAnalysis | None:
        return await self._cache.get(workout_id)

    async def generate_and_cache(
        self, athlete_id: str, workout_id: str
    ) -> CachedActivityAnalysis:
        workout = await self._workouts.get_workout(workout_id)
        if workout is None:
            raise ValueError(f"Workout {workout_id} not found")

        athlete = await self._athletes.get_default()
        recent_similar = await self._recent_similar_workouts(athlete_id, workout)
        ff = await self._fitness_freshness_at(athlete_id, workout.start_time.date())

        prompt = self._build_prompt(workout, athlete, recent_similar, ff)
        analysis = self._call_gemini(prompt)

        await self._cache.save(workout_id, analysis)
        return CachedActivityAnalysis(
            workout_id=workout_id,
            analysis=analysis,
            generated_at=datetime.now(tz=timezone.utc),
        )

    async def _recent_similar_workouts(
        self, athlete_id: str, workout: Workout
    ) -> list[Workout]:
        end_date = workout.start_time.date()
        start_date = end_date - timedelta(days=90)
        recent = await self._workouts.list_workouts_for_athlete(
            athlete_id, start_date=start_date, end_date=end_date, limit=20
        )
        same_sport = [
            w for w in recent
            if w.workout_type == workout.workout_type and w.id != workout.id
        ]
        return same_sport[:10]

    async def _fitness_freshness_at(
        self, athlete_id: str, on_date: date
    ) -> dict:
        display_days = max(1, (date.today() - on_date).days + 1)
        since = on_date - timedelta(days=CTL_SEED_DAYS + 7)
        daily_efforts = await self._analytics.daily_effort(athlete_id, since)
        ff = compute_fitness_freshness(daily_efforts, display_days)
        if not ff:
            return {"fitness": 0.0, "fatigue": 0.0, "form": 0.0, "effort": 0.0}
        return ff[0]

    def _build_prompt(
        self, workout: Workout, athlete, recent_similar: list[Workout], ff: dict
    ) -> str:
        goal_lines = [
            f"  - {g.goal_type.value}: {g.description}" for g in athlete.goals
        ]
        goals_block = "\n".join(goal_lines) or "  (no goals set)"

        injury_lines = [
            f"  - {i.affected_area}: {i.description}" for i in athlete.active_injuries
        ]
        injuries_block = "\n".join(injury_lines) or "  None"

        workout_block = self._format_workout(workout)

        if recent_similar:
            recent_block = "\n".join(
                self._format_workout_line(w) for w in recent_similar
            )
        else:
            recent_block = "  No previous similar workouts on record."

        form = ff["form"]
        if form > 5:
            form_context = "positive — athlete is fresh, can push harder"
        elif form < -10:
            form_context = "negative — fatigue accumulated, prioritise recovery"
        else:
            form_context = "neutral — balanced training load"

        return f"""You are a personal fitness coach. Analyse this workout in the context of the athlete's profile, current training load, and goals.

ATHLETE PROFILE:
- Name: {athlete.name}
- Goals:
{goals_block}
- Active injuries or limitations:
{injuries_block}
- Notes: {athlete.notes or '(none)'}

THE WORKOUT:
{workout_block}

FITNESS STATE (on the day of this workout):
- Fitness (chronic load): {ff['fitness']:.0f}
- Fatigue (acute load): {ff['fatigue']:.0f}
- Form: {form:.0f} — {form_context}
- Effort score for this session: {ff['effort']:.0f}

RECENT SIMILAR WORKOUTS (last {len(recent_similar)} {workout.workout_type.value} sessions before this one):
{recent_block}

Respond with a JSON object with exactly these fields:
{{
  "performance_assessment": "1-2 sentences on how the session went relative to the athlete's baseline",
  "training_load_context": "1-2 sentences on what the fitness/fatigue state means for this workout",
  "goal_relevance": "1-2 sentences on whether and how this workout contributes to the athlete's goals",
  "comparison_to_recent": "1-2 sentences comparing to the recent similar workouts listed above",
  "takeaway": "1 sentence — the single most actionable coaching point"
}}

Keep the tone direct, coaching, and grounded in the data. Respond with only the JSON, no other text."""

    def _format_workout(self, w: Workout) -> str:
        lines = [
            f"  Date: {w.start_time.strftime('%A %B %d, %Y')}",
            f"  Type: {w.workout_type.value}",
            f"  Name: {w.name}",
            f"  Duration: {w.duration_minutes:.0f} minutes",
        ]
        if w.distance_km:
            lines.append(f"  Distance: {w.distance_km:.1f}km")
        if w.pace_formatted():
            lines.append(f"  Pace: {w.pace_formatted()}")
        if w.average_heartrate:
            lines.append(f"  Average heart rate: {w.average_heartrate:.0f}")
        if w.max_heartrate:
            lines.append(f"  Maximum heart rate: {w.max_heartrate:.0f}")
        if w.elevation_gain_meters:
            lines.append(f"  Elevation gain: {w.elevation_gain_meters:.0f}m")
        if w.private_note:
            lines.append(f"  Notes: {w.private_note}")
        if w.perceived_effort:
            lines.append(f"  Perceived effort: {w.perceived_effort.value}")
        return "\n".join(lines)

    def _format_workout_line(self, w: Workout) -> str:
        line = f"  - {w.start_time.strftime('%a %b %d')} {w.workout_type.value} {w.duration_minutes:.0f}min"
        if w.distance_km:
            line += f" {w.distance_km:.1f}km"
        if w.pace_formatted():
            line += f" pace {w.pace_formatted()}"
        if w.average_heartrate:
            line += f" HR {w.average_heartrate:.0f}"
        return line

    async def get_chat_messages(self, workout_id: str) -> list[ChatMessage]:
        return await self._chat.list_messages(workout_id)

    async def chat(self, athlete_id: str, workout_id: str, message: str) -> str:
        workout = await self._workouts.get_workout(workout_id)
        if workout is None:
            raise ValueError(f"Workout {workout_id} not found")

        athlete = await self._athletes.get_default()
        history = await self._chat.list_messages(workout_id)
        context = self._build_chat_context(workout, athlete)
        response = self._call_gemini_chat(context, history, message)

        await self._chat.append_message(workout_id, "user", message)
        await self._chat.append_message(workout_id, "model", response)
        return response

    def _build_chat_context(self, workout: Workout, athlete) -> str:
        goal_lines = [f"  - {g.goal_type.value}: {g.description}" for g in athlete.goals]
        goals_block = "\n".join(goal_lines) or "  (no goals set)"
        return f"""You are a personal fitness coach. The athlete wants to discuss this workout.

ATHLETE: {athlete.name}
GOALS:
{goals_block}
NOTES: {athlete.notes or '(none)'}

THE WORKOUT:
{self._format_workout(workout)}

Answer their questions about this workout: how it went, what it means for their training, comparisons, recommendations, etc. Be direct and coaching. Keep answers concise."""

    def _call_gemini_chat(
        self, context: str, history: list[ChatMessage], message: str
    ) -> str:
        contents = [
            {"role": "user", "parts": [{"text": context}]},
            {"role": "model", "parts": [{"text": "Understood. I'm ready to discuss this workout with you. What would you like to know?"}]},
        ]
        for msg in history:
            contents.append({"role": msg.role, "parts": [{"text": msg.content}]})
        contents.append({"role": "user", "parts": [{"text": message}]})

        response = self._client.models.generate_content(
            model=ANALYSIS_MODEL, contents=contents
        )
        return response.text.strip()

    def _call_gemini(self, prompt: str) -> ActivityAnalysis:
        response = self._client.models.generate_content(
            model=ANALYSIS_MODEL, contents=prompt
        )
        return self._parse_response(response.text)

    def _parse_response(self, text: str) -> ActivityAnalysis:
        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(cleaned)
            return ActivityAnalysis(
                performance_assessment=data.get("performance_assessment", ""),
                training_load_context=data.get("training_load_context", ""),
                goal_relevance=data.get("goal_relevance", ""),
                comparison_to_recent=data.get("comparison_to_recent", ""),
                takeaway=data.get("takeaway", ""),
            )
        except json.JSONDecodeError:
            return ActivityAnalysis(
                performance_assessment=text,
                training_load_context="",
                goal_relevance="",
                comparison_to_recent="",
                takeaway="",
            )
