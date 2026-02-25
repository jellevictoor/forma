"""Seed data for Jelle's profile and schedule."""

import asyncio
from datetime import date
from uuid import uuid4

from fitness_coach.adapters.sqlite_storage import SQLiteStorage
from fitness_coach.domain.athlete import Athlete, Goal, GoalType
from fitness_coach.domain.schedule import (
    IntensityLevel,
    Schedule,
    ScheduledWorkout,
    TrainingPhase,
    WeekSummary,
)
from fitness_coach.domain.workout import WorkoutType


def create_athlete() -> Athlete:
    """Create Jelle's athlete profile from ChatGPT conversation."""
    return Athlete(
        id="jelle",
        name="Jelle",
        date_of_birth=date(1987, 1, 1),  # 38 years old
        weight_kg=90.0,
        height_cm=None,
        experience_years=2,  # Returning runner, was fitter in 2021
        sports_background=["running", "bouldering"],
        goals=[
            Goal(
                goal_type=GoalType.WEIGHT_LOSS,
                description="Weight loss through running, clearing my head",
                priority=1,
            ),
            Goal(
                goal_type=GoalType.GENERAL_FITNESS,
                description="Get better at bouldering (V1-V3 → solid V3)",
                priority=2,
            ),
            Goal(
                goal_type=GoalType.STRENGTH,
                description="Build strength and core stability",
                priority=3,
            ),
        ],
        injuries=[],
        preferred_workout_days=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
        max_hours_per_week=6.0,
        notes="""Returning runner - restarted in September 2025. Was fitter in 2021.
Uses AirPods Pro 3 for HR monitoring.
Wednesday: cannot leave home, home workout only.
Equipment at home: mat only (no dumbbells yet).
HR target for easy runs: 135-145 bpm.
Breakfast: banana, yoghurt, honey granola. Drinks lots of coffee + 750ml soup/day.""",
        strava_athlete_id=None,  # To be filled after Strava auth
    )


def create_schedule(athlete_id: str) -> Schedule:
    """Create Jelle's current weekly schedule from ChatGPT conversation."""

    # Weekly workouts - repeating pattern
    workouts = [
        # Monday - Run
        ScheduledWorkout(
            id=str(uuid4()),
            day_of_week=0,  # Monday
            week_number=1,
            workout_type=WorkoutType.RUN,
            intensity=IntensityLevel.EASY,
            description="Easy run - weight loss & head clearing",
            target_duration_minutes=50,
            target_pace_description="HR 135-145 bpm, conversational pace",
            notes="Ignore pace, run relaxed. Reference run: 6.71km in 48min, avg HR 135bpm.",
        ),
        # Tuesday - Core + Strength
        ScheduledWorkout(
            id=str(uuid4()),
            day_of_week=1,  # Tuesday
            week_number=1,
            workout_type=WorkoutType.STRENGTH,
            intensity=IntensityLevel.MODERATE,
            description="Core + Strength (at home)",
            target_duration_minutes=30,
            structured_workout="""3 rounds, rest 60-90s between rounds:
- Plank: 45s (long-lever, squeeze glutes)
- Bodyweight squat OR split squat: 15 (slow, 3s down)
- Push-ups: 10-12 (cap here, don't chase reps)
- Glute bridge: 15 (2s pause at top) OR single-leg 8/side
- Dead bug: 10/side (opposite arm+leg, back glued to floor)
- Bird dog hold: 10-15s each side (replaced superman)""",
            notes="Quality > volume. Never to failure. Slow tempo.",
        ),
        # Wednesday - Conditioning + Core (at home, can't leave)
        ScheduledWorkout(
            id=str(uuid4()),
            day_of_week=2,  # Wednesday
            week_number=1,
            workout_type=WorkoutType.CROSS_TRAINING,
            intensity=IntensityLevel.MODERATE,
            description="Conditioning + Core (at home)",
            target_duration_minutes=25,
            structured_workout="""Warm-up: 5min mobility/light movement

3 rounds, rest ~45s between exercises:
- Mountain climbers: 30s
- Wall sit: 45s
- Plank shoulder taps: 12-16 (slow, controlled, widen feet)
- Reverse lunges: 10/leg
- Hollow body hold: 20s (cap here)

Optional finisher (pick one):
- Shadow climbing
- Mobility flow
- Slow burpees: 5 (cap here)""",
            notes="Can't leave home. No equipment. Avg HR ~125bpm is perfect.",
        ),
        # Thursday - Bouldering
        ScheduledWorkout(
            id=str(uuid4()),
            day_of_week=3,  # Thursday
            week_number=1,
            workout_type=WorkoutType.CROSS_TRAINING,
            intensity=IntensityLevel.MODERATE,
            description="Bouldering V1-V3",
            target_duration_minutes=75,
            structured_workout="""- Warm-up: 10-15min easy traverses, V0-V1
- Work 3-4 problems max
- Focus: feet first, hip movement, controlled movement
- Rest properly between attempts
- Finish with easy sends for confidence""",
            notes="Technique session. Feet + hips. Pick one focus: 'place feet before moving hands'.",
        ),
        # Friday - Core + Climbing Support
        ScheduledWorkout(
            id=str(uuid4()),
            day_of_week=4,  # Friday
            week_number=1,
            workout_type=WorkoutType.STRENGTH,
            intensity=IntensityLevel.MODERATE,
            description="Core + Climbing Support (at home)",
            target_duration_minutes=30,
            structured_workout="""3 rounds, controlled tempo:
- Side plank: 30s/side
- Pike hold: 20-30s
- Slow push-ups: 8-10
- Isometric squat hold: 45s
- Y-T-W raises (on mat): 8 each""",
            notes="Shoulder stability, core tension for steep climbs.",
        ),
        # Saturday - Run
        ScheduledWorkout(
            id=str(uuid4()),
            day_of_week=5,  # Saturday
            week_number=1,
            workout_type=WorkoutType.RUN,
            intensity=IntensityLevel.EASY,
            description="Easy run",
            target_duration_minutes=35,
            target_pace_description="HR 135-145 bpm, easy",
            notes="Same or slightly slower than Monday. Optional short strides if feeling good.",
        ),
        # Sunday - Rest
        ScheduledWorkout(
            id=str(uuid4()),
            day_of_week=6,  # Sunday
            week_number=1,
            workout_type=WorkoutType.REST,
            intensity=IntensityLevel.RECOVERY,
            description="Rest / Mobility",
            target_duration_minutes=0,
            is_optional=True,
            notes="Full rest or gentle stretching only.",
        ),
    ]

    return Schedule(
        id="jelle-weekly-v1",
        athlete_id=athlete_id,
        name="Weekly Training Plan v1",
        description="Weight loss (running) · bouldering progression · strength. Equipment: mat only.",
        start_date=date(2025, 1, 6),  # Week started Monday Jan 6
        current_week=1,
        current_phase=TrainingPhase.BASE,
        weeks=[
            WeekSummary(
                week_number=1,
                phase=TrainingPhase.BASE,
                focus="Build consistency, establish baselines",
                total_hours=5.0,
                notes="Phase 1: improve movement quality, aerobic efficiency, body tension, build tolerance.",
            ),
        ],
        workouts=workouts,
        notes="""Key principles:
- HR target for runs: 135-145 bpm (easy, boring, conversational)
- Home workouts: quality > volume, never to failure
- Core = anti-movement (stability)
- Consistency beats hero workouts
- Recovery is part of training

Current limiters to work on:
- Anti-rotation core (plank taps)
- Hollow-body tension
- Initial quad tolerance (wall sits)
- Glute recruitment""",
    )


async def seed_database(db_path: str = "data/fitness_coach.db") -> None:
    """Seed the database with Jelle's profile and schedule."""
    storage = SQLiteStorage(db_path)

    # Create athlete
    athlete = create_athlete()
    await storage.save(athlete)
    await storage.set_default(athlete.id)
    print(f"✓ Created athlete: {athlete.name}")

    # Create schedule
    schedule = create_schedule(athlete.id)
    await storage.save_schedule(schedule)
    await storage.set_active_schedule(athlete.id, schedule.id)
    print(f"✓ Created schedule: {schedule.name}")

    print("\nDone! Run 'fitness-coach chat' to talk with your coach.")


if __name__ == "__main__":
    asyncio.run(seed_database())
