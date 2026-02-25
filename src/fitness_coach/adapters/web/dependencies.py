"""Dependency injection providers for the web adapter."""

from collections.abc import AsyncIterator
from functools import lru_cache

from fitness_coach.adapters.sqlite_analytics import SQLiteAnalyticsRepository
from fitness_coach.adapters.sqlite_plan_cache import SQLitePlanCache
from fitness_coach.adapters.sqlite_recap_cache import SQLiteRecapCache
from fitness_coach.adapters.sqlite_storage import SQLiteStorage
from fitness_coach.adapters.strava_client import StravaClient
from fitness_coach.application.analytics_service import AnalyticsService
from fitness_coach.application.athlete_profile_service import AthleteProfileService
from fitness_coach.application.sync_all_activities import FullStravaSync
from fitness_coach.application.training_insights import TrainingInsightsService
from fitness_coach.application.weekly_recap import WeeklyRecapService
from fitness_coach.application.weight_tracking_service import WeightTrackingService
from fitness_coach.application.workout_planning_service import WorkoutPlanningService
from fitness_coach.config import get_settings
from fitness_coach.ports.workout_repository import WorkoutRepository


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
    return TrainingInsightsService(analytics_repo, workout_repo, settings.gemini_api_key)


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


async def get_athlete_id() -> str:
    """Return the default athlete ID. Single-user mode."""
    settings = get_settings()
    storage = SQLiteStorage(settings.database_path)
    athlete = await storage.get_default()
    if athlete:
        return athlete.id
    return "default"
