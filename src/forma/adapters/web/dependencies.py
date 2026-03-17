"""Dependency injection providers for the web adapter."""

from collections.abc import AsyncIterator
from functools import lru_cache

from forma.adapters.sqlite_activity_analysis import SQLiteActivityAnalysis
from forma.adapters.sqlite_analytics import SQLiteAnalyticsRepository
from forma.adapters.sqlite_chat import SQLiteChat
from forma.adapters.sqlite_execution_session import SQLiteExecutionSession
from forma.adapters.sqlite_insights_cache import SQLiteInsightsCache
from forma.adapters.sqlite_plan_cache import SQLitePlanCache
from forma.adapters.sqlite_recap_cache import SQLiteRecapCache
from forma.adapters.sqlite_storage import SQLiteStorage
from forma.adapters.strava_client import StravaClient
from forma.application.analytics_service import AnalyticsService
from forma.application.athlete_profile_service import AthleteProfileService
from forma.application.sync_all_activities import FullStravaSync
from forma.application.training_insights import TrainingInsightsService
from forma.application.weekly_recap import WeeklyRecapService
from forma.application.weight_tracking_service import WeightTrackingService
from forma.application.activity_analysis_service import ActivityAnalysisService
from forma.application.workout_execution_service import WorkoutExecutionService
from forma.application.workout_planning_service import WorkoutPlanningService
from forma.config import get_settings
from forma.ports.workout_repository import WorkoutRepository


@lru_cache
def _create_analytics_service() -> AnalyticsService:
    settings = get_settings()
    db_path = settings.database_path
    analytics_repo = SQLiteAnalyticsRepository(db_path)
    workout_repo = SQLiteStorage(db_path)
    return AnalyticsService(analytics_repo, workout_repo)


@lru_cache
def _create_insights_service() -> TrainingInsightsService:
    settings = get_settings()
    db_path = settings.database_path
    analytics_repo = SQLiteAnalyticsRepository(db_path)
    workout_repo = SQLiteStorage(db_path)
    cache_repo = SQLiteInsightsCache(db_path)
    return TrainingInsightsService(analytics_repo, workout_repo, settings.gemini_api_key, cache_repo)


@lru_cache
def _create_weekly_recap_service() -> WeeklyRecapService:
    settings = get_settings()
    db_path = settings.database_path
    analytics_repo = SQLiteAnalyticsRepository(db_path)
    workout_repo = SQLiteStorage(db_path)
    cache_repo = SQLiteRecapCache(db_path)
    return WeeklyRecapService(analytics_repo, workout_repo, settings.gemini_api_key, cache_repo)


@lru_cache
def _create_workout_repo() -> WorkoutRepository:
    settings = get_settings()
    return SQLiteStorage(settings.database_path)


async def get_weekly_recap_service() -> WeeklyRecapService:
    return _create_weekly_recap_service()


async def get_insights_service() -> TrainingInsightsService:
    return _create_insights_service()


async def get_analytics_service() -> AnalyticsService:
    return _create_analytics_service()


async def get_workout_repo() -> WorkoutRepository:
    return _create_workout_repo()


@lru_cache
def _create_athlete_profile_service() -> AthleteProfileService:
    settings = get_settings()
    db_path = settings.database_path
    storage = SQLiteStorage(db_path)
    return AthleteProfileService(storage, storage, settings.gemini_api_key)


@lru_cache
def _create_weight_tracking_service() -> WeightTrackingService:
    settings = get_settings()
    storage = SQLiteStorage(settings.database_path)
    return WeightTrackingService(storage)


async def get_athlete_profile_service() -> AthleteProfileService:
    return _create_athlete_profile_service()


async def get_weight_tracking_service() -> WeightTrackingService:
    return _create_weight_tracking_service()


@lru_cache
def _create_workout_planning_service() -> WorkoutPlanningService:
    settings = get_settings()
    db_path = settings.database_path
    athlete_repo = SQLiteStorage(db_path)
    workout_repo = SQLiteStorage(db_path)
    analytics_repo = SQLiteAnalyticsRepository(db_path)
    plan_cache = SQLitePlanCache(db_path)
    return WorkoutPlanningService(athlete_repo, workout_repo, analytics_repo, settings.gemini_api_key, plan_cache)


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
        yield FullStravaSync(client, SQLiteStorage(settings.database_path))
    finally:
        await client.close()


@lru_cache
def _create_activity_analysis_service() -> ActivityAnalysisService:
    settings = get_settings()
    db_path = settings.database_path
    workout_repo = SQLiteStorage(db_path)
    analytics_repo = SQLiteAnalyticsRepository(db_path)
    athlete_repo = SQLiteStorage(db_path)
    cache_repo = SQLiteActivityAnalysis(db_path)
    chat_repo = SQLiteChat(db_path)
    return ActivityAnalysisService(workout_repo, analytics_repo, athlete_repo, settings.gemini_api_key, cache_repo, chat_repo)


async def get_activity_analysis_service() -> ActivityAnalysisService:
    return _create_activity_analysis_service()


@lru_cache
def _create_workout_execution_service() -> WorkoutExecutionService:
    settings = get_settings()
    db_path = settings.database_path
    session_repo = SQLiteExecutionSession(db_path)
    planning_service = _create_workout_planning_service()
    return WorkoutExecutionService(session_repo, planning_service)


async def get_workout_execution_service() -> WorkoutExecutionService:
    return _create_workout_execution_service()


async def get_athlete_id() -> str:
    """Return the default athlete ID. Single-user mode."""
    settings = get_settings()
    storage = SQLiteStorage(settings.database_path)
    athlete = await storage.get_default()
    if athlete:
        return athlete.id
    return "default"
