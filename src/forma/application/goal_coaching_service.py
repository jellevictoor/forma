"""Goal coaching service — conversational, data-grounded goal setting with Gemini."""

import json
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from google import genai

from forma.domain.athlete import Athlete, Goal, GoalMilestone, GoalType
from forma.ports.athlete_repository import AthleteRepository
from forma.ports.workout_repository import WorkoutRepository

COACHING_MODEL = "models/gemini-2.5-flash"

logger = logging.getLogger(__name__)

_GOAL_TYPES = {t.value for t in GoalType}


@dataclass
class WeeklyVolume:
    week_start: date
    distance_km: float
    run_count: int
    avg_pace_sec_per_km: float | None


@dataclass
class TrainingSnapshot:
    """Key training metrics for the last 90 days — fed to the coaching context."""

    recent_runs: list  # last 10 run workouts
    weekly_volumes: list[WeeklyVolume]
    avg_runs_per_week: float
    avg_distance_km: float
    avg_pace_sec_per_km: float | None
    longest_run_km: float | None
    total_runs_90d: int
    has_hr_data: bool
    avg_heartrate: float | None


@dataclass
class ChatMessage:
    role: str  # "user" | "model"
    text: str


@dataclass
class GoalProposal:
    goal_type: str
    description: str
    target_value: str | None
    target_date: date | None
    milestones: list[dict]
    rationale: str


_SYSTEM_PROMPT_TEMPLATE = """\
You are an experienced, data-driven personal fitness coach inside the "forma" app.
Your job right now is to help the athlete set a realistic, meaningful fitness goal.

You have access to their full training history. Use it. Don't guess — reference actual numbers.

## Coaching principles
- Prioritise injury prevention and long-term consistency over short-term performance.
- Be direct. Give clear recommendations, not wishy-washy suggestions.
- Ground every claim in the athlete's actual data.
- Be encouraging but honest. If a goal is unrealistic, say so — and explain why using the data.
- Aerobic base first. Speed and performance come later.
- A goal should stretch but not break the athlete.

## Athlete profile
Name: {name}
Age: {age}
Experience: {experience_years} years of training
Max hours/week available: {max_hours}
Notes: {notes}
Equipment: {equipment}
Max heart rate: {max_hr}
Zone 2 ceiling (talk test): {vt1}

## Training snapshot — last 90 days
Total runs: {total_runs}
Average runs/week: {avg_runs_per_week:.1f}
Average run distance: {avg_distance:.1f} km
Longest run: {longest_run}
Average pace: {avg_pace}
Average HR during runs: {avg_hr}
Weekly volume trend (newest first):
{volume_table}

## Recent runs (last 10)
{recent_runs}

## Goal history
{goal_history}

## Weekly schedule template
{schedule}

## How to run this conversation

1. Open with a brief, specific observation about their current fitness — one or two things you actually see in the data. Not generic praise.
2. Ask what they want to achieve.
3. If they name something vague ("get fitter", "lose weight"), ask for a more concrete outcome.
4. Once you understand their aspiration, give your honest assessment:
   - Is it realistic given their current level?
   - What's a better target if theirs is off?
   - What time frame is appropriate?
5. Propose 2-3 milestones with dates and measurable targets.
6. When the athlete agrees on a specific goal, output a structured proposal using EXACTLY this format — do not deviate:

<<GOAL_PROPOSAL>>
{{
  "goal_type": "<one of: race, time_goal, distance_goal, general_fitness, weight_loss, strength>",
  "description": "<one clear sentence>",
  "target_value": "<measurable target, e.g. sub-52min 10k, or null>",
  "target_date": "<YYYY-MM-DD or null>",
  "milestones": [
    {{"date": "YYYY-MM-DD", "description": "<what this checkpoint means>", "target": "<measurable or null>"}},
    {{"date": "YYYY-MM-DD", "description": "...", "target": "..."}}
  ],
  "rationale": "<2-3 sentences: why this goal, why this timeline, based on their specific data>"
}}
<<END_PROPOSAL>>

Only output the proposal block once the athlete has explicitly said yes to a specific goal.
Do not output the proposal block during the negotiation phase.
After outputting the proposal, add a short human sentence like "Does this look right? Hit Accept to save it."
"""

_START_PROMPT = """\
The athlete has just opened the goal-setting session. Write your opening message.
- Reference 1-2 specific data points from their training snapshot.
- Keep it concise: 2-3 sentences max.
- End with a single open question about what they want to achieve.
Do not output a GOAL_PROPOSAL yet.
"""


class GoalCoachingService:
    """Conversational, data-grounded goal-setting powered by Gemini."""

    def __init__(
        self,
        athlete_repo: AthleteRepository,
        workout_repo: WorkoutRepository,
        gemini_api_key: str,
    ) -> None:
        self._athletes = athlete_repo
        self._workouts = workout_repo
        self._client = genai.Client(api_key=gemini_api_key)

    async def build_snapshot(self, athlete_id: str) -> TrainingSnapshot:
        since = datetime.now() - timedelta(days=90)
        workouts = await self._workouts.get_recent(athlete_id, count=200)
        runs = [w for w in workouts if w.workout_type.value == "run" and w.start_time >= since]
        runs.sort(key=lambda w: w.start_time, reverse=True)

        weekly: dict[date, list] = {}
        for run in runs:
            week_start = run.start_time.date() - timedelta(days=run.start_time.weekday())
            weekly.setdefault(week_start, []).append(run)

        weekly_volumes = [
            WeeklyVolume(
                week_start=ws,
                distance_km=sum(r.distance_km or 0 for r in rs),
                run_count=len(rs),
                avg_pace_sec_per_km=_avg_pace(rs),
            )
            for ws, rs in sorted(weekly.items(), reverse=True)
        ]

        pace_vals = [r.pace_min_per_km for r in runs if r.pace_min_per_km]
        hr_vals = [r.average_heartrate for r in runs if r.average_heartrate]

        return TrainingSnapshot(
            recent_runs=runs[:10],
            weekly_volumes=weekly_volumes[:8],
            avg_runs_per_week=len(runs) / (90 / 7),
            avg_distance_km=sum(r.distance_km or 0 for r in runs) / max(1, len(runs)),
            avg_pace_sec_per_km=sum(pace_vals) / len(pace_vals) * 60 if pace_vals else None,
            longest_run_km=max((r.distance_km or 0 for r in runs), default=None),
            total_runs_90d=len(runs),
            has_hr_data=bool(hr_vals),
            avg_heartrate=sum(hr_vals) / len(hr_vals) if hr_vals else None,
        )

    async def start(self, athlete_id: str) -> str:
        """Generate the opening coach message for a new goal-setting session."""
        athlete = await self._athletes.get(athlete_id)
        if not athlete:
            raise ValueError(f"Athlete {athlete_id} not found")
        snapshot = await self.build_snapshot(athlete_id)
        system = self._build_system_prompt(athlete, snapshot)
        contents = [
            {"role": "user", "parts": [{"text": system + "\n\n" + _START_PROMPT}]},
        ]
        logger.info("goal coaching: generating opening message for %s", athlete_id)
        response = self._client.models.generate_content(model=COACHING_MODEL, contents=contents)
        return response.text.strip()

    async def chat(
        self,
        athlete_id: str,
        message: str,
        history: list[dict],
    ) -> str:
        """Continue the coaching conversation. History is [{role, text}, ...]."""
        athlete = await self._athletes.get(athlete_id)
        if not athlete:
            raise ValueError(f"Athlete {athlete_id} not found")
        snapshot = await self.build_snapshot(athlete_id)
        system = self._build_system_prompt(athlete, snapshot)

        contents = [
            {"role": "user", "parts": [{"text": system}]},
            {"role": "model", "parts": [{"text": "Understood. I have the athlete's full context."}]},
        ]
        for msg in history:
            contents.append({"role": msg["role"], "parts": [{"text": msg["text"]}]})
        contents.append({"role": "user", "parts": [{"text": message}]})

        logger.info("goal coaching: chat turn for %s (history len %d)", athlete_id, len(history))
        response = self._client.models.generate_content(model=COACHING_MODEL, contents=contents)
        return response.text.strip()

    def extract_proposal(self, text: str) -> GoalProposal | None:
        """Extract a structured goal proposal from coach response text, if present."""
        match = re.search(r"<<GOAL_PROPOSAL>>(.*?)<<END_PROPOSAL>>", text, re.DOTALL)
        if not match:
            return None
        try:
            data = json.loads(match.group(1).strip())
            target_date = None
            if data.get("target_date"):
                target_date = date.fromisoformat(data["target_date"])
            milestones = []
            for m in data.get("milestones", []):
                milestones.append({
                    "date": m["date"],
                    "description": m["description"],
                    "target": m.get("target"),
                })
            return GoalProposal(
                goal_type=data.get("goal_type", "general_fitness"),
                description=data.get("description", ""),
                target_value=data.get("target_value"),
                target_date=target_date,
                milestones=milestones,
                rationale=data.get("rationale", ""),
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            logger.warning("goal coaching: failed to parse proposal from response")
            return None

    async def save_proposal(self, athlete_id: str, proposal: GoalProposal) -> Goal:
        """Convert a confirmed proposal into a Goal and save it."""
        athlete = await self._athletes.get(athlete_id)
        if not athlete:
            raise ValueError(f"Athlete {athlete_id} not found")

        goal_type = GoalType(proposal.goal_type) if proposal.goal_type in _GOAL_TYPES else GoalType.GENERAL_FITNESS
        milestones = [
            GoalMilestone(
                date=date.fromisoformat(m["date"]),
                description=m["description"],
                target=m.get("target"),
            )
            for m in proposal.milestones
        ]
        goal = Goal(
            goal_type=goal_type,
            description=proposal.description,
            target_value=proposal.target_value,
            target_date=proposal.target_date,
            milestones=milestones,
            coach_rationale=proposal.rationale,
        )
        updated = athlete.with_primary_goal(goal)
        await self._athletes.save(updated)
        logger.info("goal coaching: saved new goal for %s: %s", athlete_id, goal.description)
        return goal

    def _build_system_prompt(self, athlete: Athlete, snapshot: TrainingSnapshot) -> str:
        age_str = f"{athlete.age}" if athlete.age else "unknown"
        max_hr_str = str(athlete.max_heartrate) if athlete.max_heartrate else "not set (using 220−age estimate)"
        vt1_str = f"{athlete.aerobic_threshold_bpm} bpm (talk-test calibrated)" if athlete.aerobic_threshold_bpm else "not set"

        volume_lines = []
        for wv in snapshot.weekly_volumes:
            pace_str = _format_pace(wv.avg_pace_sec_per_km) if wv.avg_pace_sec_per_km else "—"
            volume_lines.append(
                f"  {wv.week_start.strftime('%d %b')}: {wv.distance_km:.1f} km over {wv.run_count} run(s), avg pace {pace_str}"
            )
        volume_table = "\n".join(volume_lines) or "  No runs in last 90 days."

        recent_run_lines = []
        for run in snapshot.recent_runs:
            pace_str = run.pace_formatted() or "—"
            hr_str = f" HR {run.average_heartrate:.0f}" if run.average_heartrate else ""
            recent_run_lines.append(
                f"  {run.start_time.strftime('%d %b')} — {run.distance_km or 0:.1f} km, {run.duration_minutes:.0f} min, pace {pace_str}{hr_str}"
            )
        recent_runs_block = "\n".join(recent_run_lines) or "  None."

        avg_pace_str = _format_pace(snapshot.avg_pace_sec_per_km) if snapshot.avg_pace_sec_per_km else "unknown"
        avg_hr_str = f"{snapshot.avg_heartrate:.0f} bpm" if snapshot.avg_heartrate else "no HR data"
        longest_str = f"{snapshot.longest_run_km:.1f} km" if snapshot.longest_run_km else "unknown"

        if athlete.goal_history:
            sorted_history = sorted(athlete.goal_history, key=lambda e: e.set_at)
            goal_lines = [
                f"  [{e.set_at.strftime('%d %b %Y')} → {e.retired_at.strftime('%d %b %Y')}] {e.goal_type.value}: {e.description}"
                for e in sorted_history
            ]
            goal_history_block = "\n".join(goal_lines)
        elif athlete.primary_goal:
            goal_history_block = f"  Current: {athlete.primary_goal.description} (since {athlete.primary_goal.set_at.strftime('%d %b %Y')})"
        else:
            goal_history_block = "  No goals set yet."

        if athlete.schedule_template:
            days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            schedule_lines = [f"  {days[s.day_of_week]}: {s.workout_type.value}" for s in athlete.schedule_template]
            schedule_block = "\n".join(schedule_lines)
        else:
            schedule_block = "  Not configured."

        equipment_block = ", ".join(athlete.equipment) if athlete.equipment else "not specified — assume bodyweight only"

        return _SYSTEM_PROMPT_TEMPLATE.format(
            name=athlete.name,
            age=age_str,
            experience_years=athlete.experience_years,
            max_hours=athlete.max_hours_per_week or "not set",
            notes=athlete.notes or "none",
            equipment=equipment_block,
            max_hr=max_hr_str,
            vt1=vt1_str,
            total_runs=snapshot.total_runs_90d,
            avg_runs_per_week=snapshot.avg_runs_per_week,
            avg_distance=snapshot.avg_distance_km,
            longest_run=longest_str,
            avg_pace=avg_pace_str,
            avg_hr=avg_hr_str,
            volume_table=volume_table,
            recent_runs=recent_runs_block,
            goal_history=goal_history_block,
            schedule=schedule_block,
        )


def _avg_pace(runs: list) -> float | None:
    paces = [r.pace_min_per_km for r in runs if r.pace_min_per_km]
    return (sum(paces) / len(paces)) * 60 if paces else None


def _format_pace(sec_per_km: float) -> str:
    m = int(sec_per_km // 60)
    s = int(sec_per_km % 60)
    return f"{m}:{s:02d}/km"
