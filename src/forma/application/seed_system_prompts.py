"""Seed default system prompts into the database on startup."""

from forma.application.activity_analysis_service import _SYSTEM_INSTRUCTION as ANALYSIS_PROMPT
from forma.application.goal_coaching_service import _SYSTEM_INSTRUCTION as COACHING_PROMPT
from forma.application.workout_planning_service import _SYSTEM_INSTRUCTION as PLANNING_PROMPT
from forma.ports.system_prompt_repository import SystemPrompt, SystemPromptRepository

DEFAULTS = [
    SystemPrompt(
        service="activity-analysis",
        label="Activity analysis",
        text=ANALYSIS_PROMPT,
    ),
    SystemPrompt(
        service="goal-coach",
        label="Goal coaching",
        text=COACHING_PROMPT,
    ),
    SystemPrompt(
        service="plan",
        label="Workout planning",
        text=PLANNING_PROMPT,
    ),
]


async def seed(repo: SystemPromptRepository) -> None:
    """Insert default prompts that don't already exist."""
    await repo.seed_defaults(DEFAULTS)
