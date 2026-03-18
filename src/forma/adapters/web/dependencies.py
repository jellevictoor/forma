"""Dependency injection providers for the web adapter."""

from collections.abc import AsyncIterator
from functools import lru_cache

from forma.adapters.postgres_activity_analysis import PostgresActivityAnalysis
from forma.adapters.postgres_analytics import PostgresAnalyticsRepository
from forma.adapters.postgres_chat import PostgresChat
from forma.adapters.postgres_execution_session import PostgresExecutionSession
from forma.adapters.postgres_insights_cache import PostgresInsightsCache
from forma.adapters.postgres_plan_cache import PostgresPlanCache
from forma.adapters.postgres_pool import get_pool
from forma.adapters.postgres_recap_cache import PostgresRecapCache
from forma.adapters.postgres_storage import PostgresStorage
from forma.adapters.postgres_stream_repository import PostgresStreamRepository
from forma.adapters.strava_client import StravaClient
from forma.application.activity_analysis_service import ActivityAnalysisService
from forma.application.activity_stream_service import ActivityStreamService
from forma.application.analytics_service import AnalyticsService
from forma.application.athlete_profile_service import AthleteProfileService
from forma.application.sync_all_activities import FullStravaSync
from forma.application.training_insights import TrainingInsightsService
from forma.application.weekly_recap import WeeklyRecapService
from forma.application.weight_tracking_service import WeightTrackingService
from forma.application.workout_execution_service import WorkoutExecutionService
from forma.application.goal_coaching_service import GoalCoachingService
from forma.application.workout_planning_service import WorkoutPlanningService
from forma.config import get_settings
from forma.ports.workout_repository import WorkoutRepository


@lru_cache
def _create_analytics_service() -> AnalyticsService:
    pool = get_pool()
    return AnalyticsService(PostgresAnalyticsRepository(pool), PostgresStorage(pool))


@lru_cache
def _create_insights_service() -> TrainingInsightsService:
    settings = get_settings()
    pool = get_pool()
    return TrainingInsightsService(
        PostgresAnalyticsRepository(pool),
        PostgresStorage(pool),
        settings.gemini_api_key,
        PostgresInsightsCache(pool),
    )


@lru_cache
def _create_weekly_recap_service() -> WeeklyRecapService:
    settings = get_settings()
    pool = get_pool()
    return WeeklyRecapService(
        PostgresAnalyticsRepository(pool),
        PostgresStorage(pool),
        settings.gemini_api_key,
        PostgresRecapCache(pool),
    )


@lru_cache
def _create_workout_repo() -> WorkoutRepository:
    return PostgresStorage(get_pool())


async def get_weekly_recap_service() -> WeeklyRecapService:
    return _create_weekly_recap_service()


async def get_insights_service() -> TrainingInsightsService:
    return _create_insights_service()


async def get_analytics_service() -> AnalyticsService:
    return _create_analytics_service()


async def get_workout_repo() -> WorkoutRepository:
    return _create_workout_repo()


@lru_cache
def _create_goal_coaching_service() -> GoalCoachingService:
    settings = get_settings()
    pool = get_pool()
    storage = PostgresStorage(pool)
    return GoalCoachingService(storage, storage, settings.gemini_api_key, PostgresChat(pool))


async def get_goal_coaching_service() -> GoalCoachingService:
    return _create_goal_coaching_service()


@lru_cache
def _create_athlete_profile_service() -> AthleteProfileService:
    settings = get_settings()
    pool = get_pool()
    storage = PostgresStorage(pool)
    return AthleteProfileService(storage, storage, settings.gemini_api_key)


@lru_cache
def _create_weight_tracking_service() -> WeightTrackingService:
    return WeightTrackingService(PostgresStorage(get_pool()))


async def get_athlete_profile_service() -> AthleteProfileService:
    return _create_athlete_profile_service()


async def get_weight_tracking_service() -> WeightTrackingService:
    return _create_weight_tracking_service()


@lru_cache
def _create_workout_planning_service() -> WorkoutPlanningService:
    settings = get_settings()
    pool = get_pool()
    return WorkoutPlanningService(
        PostgresStorage(pool),
        PostgresStorage(pool),
        PostgresAnalyticsRepository(pool),
        settings.gemini_api_key,
        PostgresPlanCache(pool),
    )


async def get_workout_planning_service() -> WorkoutPlanningService:
    return _create_workout_planning_service()


async def get_strava_sync() -> AsyncIterator[FullStravaSync]:
    """Create a FullStravaSync instance, ensuring the HTTP client is closed after use."""
    settings = get_settings()
    client = StravaClient(
        client_id=settings.strava_client_id,
        client_secret=settings.strava_client_secret,
        access_token=settings.strava_access_token,
        refresh_token=settings.strava_refresh_token,
    )
    try:
        yield FullStravaSync(client, PostgresStorage(get_pool()))
    finally:
        await client.close()


@lru_cache
def _create_activity_analysis_service() -> ActivityAnalysisService:
    settings = get_settings()
    pool = get_pool()
    return ActivityAnalysisService(
        PostgresStorage(pool),
        PostgresAnalyticsRepository(pool),
        PostgresStorage(pool),
        settings.gemini_api_key,
        PostgresActivityAnalysis(pool),
        PostgresChat(pool),
    )


async def get_activity_analysis_service() -> ActivityAnalysisService:
    return _create_activity_analysis_service()


@lru_cache
def _create_workout_execution_service() -> WorkoutExecutionService:
    pool = get_pool()
    return WorkoutExecutionService(
        PostgresExecutionSession(pool),
        _create_workout_planning_service(),
    )


async def get_workout_execution_service() -> WorkoutExecutionService:
    return _create_workout_execution_service()


@lru_cache
def _create_activity_stream_service() -> ActivityStreamService:
    settings = get_settings()
    pool = get_pool()
    client = StravaClient(
        client_id=settings.strava_client_id,
        client_secret=settings.strava_client_secret,
        access_token=settings.strava_access_token,
        refresh_token=settings.strava_refresh_token,
    )
    return ActivityStreamService(
        PostgresStorage(pool),
        PostgresStreamRepository(pool),
        client,
    )


async def get_activity_stream_service() -> ActivityStreamService:
    return _create_activity_stream_service()


async def get_athlete_id() -> str:
    """Return the default athlete ID. Single-user mode."""
    storage = PostgresStorage(get_pool())
    athlete = await storage.get_default()
    if athlete:
        return athlete.id
    return "default"
