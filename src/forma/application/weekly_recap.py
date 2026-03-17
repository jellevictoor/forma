"""Weekly training recap — AI summary of the past 7 days."""

import json
from datetime import date, datetime, timedelta, timezone

from google import genai

from forma.application.analytics_service import compute_fitness_freshness
from forma.ports.recap_cache_repository import (
    CachedRecap,
    RecapCacheRepository,
    WeeklyRecap,
)
from forma.ports.workout_analytics_repository import WorkoutAnalyticsRepository
from forma.ports.workout_repository import WorkoutRepository

RECAP_MODEL = "models/gemini-2.5-flash"


class WeeklyRecapService:
    """Generates a weekly training recap using Gemini."""

    def __init__(
        self,
        analytics_repo: WorkoutAnalyticsRepository,
        workout_repo: WorkoutRepository,
        gemini_api_key: str,
        cache_repo: RecapCacheRepository,
    ) -> None:
        self._analytics = analytics_repo
        self._workouts = workout_repo
        self._client = genai.Client(api_key=gemini_api_key)
        self._cache = cache_repo

    async def get_cached(self, athlete_id: str) -> CachedRecap | None:
        """Return the cached recap without calling the LLM."""
        return await self._cache.get(athlete_id)

    async def generate_and_cache(self, athlete_id: str) -> CachedRecap:
        """Call the LLM, persist the result, and return a CachedRecap."""
        recap = await self._generate(athlete_id)
        recent = await self._workouts.get_recent(athlete_id, count=1)
        latest_activity_at = recent[0].start_time if recent else None
        await self._cache.save(athlete_id, recap, latest_activity_at)
        return CachedRecap(
            summary=recap.summary,
            highlight=recap.highlight,
            form_note=recap.form_note,
            focus=recap.focus,
            generated_at=datetime.now(tz=timezone.utc),
            latest_activity_at=latest_activity_at,
        )

    async def _generate(self, athlete_id: str) -> WeeklyRecap:
        today = date.today()
        week_start = today - timedelta(days=6)
        prev_week_start = week_start - timedelta(days=7)

        recent = await self._workouts.get_recent(athlete_id, count=30)
        this_week = [w for w in recent if w.start_time.date() >= week_start]

        if not this_week:
            return WeeklyRecap(
                summary="No workouts recorded this week.",
                highlight="",
                form_note="",
                focus=[],
            )

        prev_week = [w for w in recent if prev_week_start <= w.start_time.date() < week_start]
        current_ff = await self._current_fitness_freshness(athlete_id)

        prompt = self._build_prompt(this_week, prev_week, current_ff)
        return self._call_gemini(prompt)

    async def _current_fitness_freshness(self, athlete_id: str) -> dict:
        since = date.today() - timedelta(days=42 * 2 + 7)
        daily_efforts = await self._analytics.daily_effort(athlete_id, since)
        ff = compute_fitness_freshness(daily_efforts, display_days=1)
        return ff[-1] if ff else {"fitness": 0.0, "fatigue": 0.0, "form": 0.0}

    def _build_prompt(self, this_week: list, prev_week: list, ff: dict) -> str:
        def fmt_workout(w) -> str:
            line = f"- {w.start_time.strftime('%a %b %d')} {w.workout_type.value}"
            if w.distance_km:
                line += f" {w.distance_km:.1f}km"
            line += f" {w.duration_minutes:.0f}min"
            if w.pace_formatted():
                line += f" pace {w.pace_formatted()}"
            if w.average_heartrate:
                line += f" HR {w.average_heartrate:.0f}"
            return line

        this_block = "\n".join(fmt_workout(w) for w in this_week)
        prev_block = "\n".join(fmt_workout(w) for w in prev_week) if prev_week else "No workouts."

        form = ff["form"]
        if form > 5:
            form_context = "positive (athlete is fresh and ready to push)"
        elif form < -10:
            form_context = "negative (accumulated fatigue — normal during a training block)"
        else:
            form_context = "neutral (balanced training load)"

        return f"""You are a personal fitness coach. Analyse this athlete's training week and write a brief, motivating recap.

THIS WEEK:
{this_block}

PREVIOUS WEEK (for comparison):
{prev_block}

CURRENT TRAINING STATE:
Fitness (42-day load): {ff["fitness"]:.0f}
Fatigue (7-day load): {ff["fatigue"]:.0f}
Form (Fitness - Fatigue): {form:.0f} — {form_context}

Respond with a JSON object with exactly these fields:
{{
  "summary": "1-2 sentences describing what the athlete did this week and how it compares to last week",
  "highlight": "1 sentence about the most notable thing this week (improvement, consistency, milestone, or honest observation)",
  "form_note": "1 sentence interpreting the current form score and what it means for the coming week",
  "focus": ["specific actionable tip for next week", "tip 2", "tip 3"]
}}

Keep the tone direct, coaching, and grounded in the data. Respond with only the JSON, no other text."""

    def _call_gemini(self, prompt: str) -> WeeklyRecap:
        response = self._client.models.generate_content(model=RECAP_MODEL, contents=prompt)
        return self._parse_response(response.text)

    def _parse_response(self, text: str) -> WeeklyRecap:
        try:
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            data = json.loads(cleaned)
            return WeeklyRecap(
                summary=data.get("summary", ""),
                highlight=data.get("highlight", ""),
                form_note=data.get("form_note", ""),
                focus=data.get("focus", []),
            )
        except json.JSONDecodeError:
            return WeeklyRecap(summary=text, highlight="", form_note="", focus=[])
