"""Dependency injection providers for the web adapter."""

from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import HTTPException, Request

from forma.adapters.postgres_activity_analysis import PostgresActivityAnalysis
from forma.adapters.postgres_analytics import PostgresAnalyticsRepository
from forma.adapters.postgres_chat import PostgresChat
from forma.adapters.postgres_execution_session import PostgresExecutionSession
from forma.adapters.postgres_plan_cache import PostgresPlanCache
from forma.adapters.postgres_pool import get_pool
from forma.adapters.postgres_system_prompts import PostgresSystemPrompts

from forma.adapters.postgres_session_repository import PostgresSessionRepository
from forma.adapters.postgres_storage import PostgresStorage
from forma.adapters.postgres_stream_repository import PostgresStreamRepository
from forma.adapters.strava_client import StravaClient
from forma.application.activity_analysis_service import ActivityAnalysisService
from forma.application.activity_stream_service import ActivityStreamService
from forma.application.analytics_service import AnalyticsService
from forma.application.athlete_profile_service import AthleteProfileService
from forma.application.sync_all_activities import FullStravaSync
from forma.application.plan_adherence import PlanAdherenceService
from forma.application.plan_skip_service import PlanSkipService
from forma.application.training_alerts import TrainingAlertsService
from forma.application.workout_enrichment import WorkoutEnrichmentService

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
def _create_workout_repo() -> WorkoutRepository:
    return PostgresStorage(get_pool())


@lru_cache
def _create_training_alerts_service() -> TrainingAlertsService:
    pool = get_pool()
    return TrainingAlertsService(
        PostgresStorage(pool),
        PostgresAnalyticsRepository(pool),
        PostgresPlanCache(pool),
        PostgresStorage(pool),
    )


async def get_training_alerts_service() -> TrainingAlertsService:
    return _create_training_alerts_service()




async def get_analytics_service() -> AnalyticsService:
    return _create_analytics_service()


async def get_workout_repo() -> WorkoutRepository:
    return _create_workout_repo()


@lru_cache
def _create_goal_coaching_service() -> GoalCoachingService:
    pool = get_pool()
    storage = PostgresStorage(pool)
    return GoalCoachingService(storage, storage, PostgresChat(pool), PostgresSystemPrompts(pool))


async def get_goal_coaching_service() -> GoalCoachingService:
    return _create_goal_coaching_service()


@lru_cache
def _create_athlete_profile_service() -> AthleteProfileService:
    pool = get_pool()
    storage = PostgresStorage(pool)
    return AthleteProfileService(storage, storage)


@lru_cache
def _create_weight_tracking_service() -> WeightTrackingService:
    return WeightTrackingService(PostgresStorage(get_pool()))


async def get_athlete_profile_service() -> AthleteProfileService:
    return _create_athlete_profile_service()


async def get_weight_tracking_service() -> WeightTrackingService:
    return _create_weight_tracking_service()


@lru_cache
def _create_workout_planning_service() -> WorkoutPlanningService:
    pool = get_pool()
    return WorkoutPlanningService(
        PostgresStorage(pool),
        PostgresStorage(pool),
        PostgresAnalyticsRepository(pool),
        PostgresPlanCache(pool),
        PostgresSystemPrompts(pool),
    )


async def get_workout_planning_service() -> WorkoutPlanningService:
    return _create_workout_planning_service()


@lru_cache
def _create_plan_adherence_service() -> PlanAdherenceService:
    pool = get_pool()
    return PlanAdherenceService(PostgresPlanCache(pool), PostgresStorage(pool))


async def get_plan_adherence_service() -> PlanAdherenceService:
    return _create_plan_adherence_service()


@lru_cache
def _create_plan_skip_service() -> PlanSkipService:
    pool = get_pool()
    return PlanSkipService(PostgresPlanCache(pool), PostgresStorage(pool))


async def get_plan_skip_service() -> PlanSkipService:
    return _create_plan_skip_service()


async def _create_strava_client(request: Request) -> tuple[StravaClient, PostgresStorage]:
    """Resolve Strava tokens from session and return a client + storage pair."""
    settings = get_settings()
    pool = get_pool()
    storage = PostgresStorage(pool)

    access_token = settings.strava_access_token
    refresh_token = settings.strava_refresh_token

    token = request.cookies.get("session")
    if token:
        session_repo = PostgresSessionRepository(pool)
        session = await session_repo.get_by_token(token)
        if session:
            athlete = await storage.get(session.athlete_id)
            if athlete and athlete.strava_access_token:
                access_token = athlete.strava_access_token
                refresh_token = athlete.strava_refresh_token

    client = StravaClient(
        client_id=settings.strava_client_id,
        client_secret=settings.strava_client_secret,
        access_token=access_token,
        refresh_token=refresh_token,
    )
    return client, storage


async def get_strava_sync(request: Request) -> AsyncIterator[FullStravaSync]:
    """Create a FullStravaSync using the authenticated athlete's stored Strava tokens."""
    client, storage = await _create_strava_client(request)
    try:
        yield FullStravaSync(client, storage, storage, PostgresPlanCache(get_pool()))
    finally:
        await client.close()


@lru_cache
def _create_activity_analysis_service() -> ActivityAnalysisService:
    pool = get_pool()
    return ActivityAnalysisService(
        PostgresStorage(pool),
        PostgresAnalyticsRepository(pool),
        PostgresStorage(pool),
        PostgresActivityAnalysis(pool),
        PostgresChat(pool),
        PostgresSystemPrompts(pool),
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


async def get_workout_enrichment_service(request: Request) -> AsyncIterator[WorkoutEnrichmentService]:
    """Create a WorkoutEnrichmentService with Strava tokens for on-demand detail fetching."""
    client, storage = await _create_strava_client(request)
    try:
        yield WorkoutEnrichmentService(client, storage)
    finally:
        await client.close()


async def get_activity_stream_service(request: Request) -> AsyncIterator[ActivityStreamService]:
    client, storage = await _create_strava_client(request)
    pool = get_pool()
    try:
        yield ActivityStreamService(storage, PostgresStreamRepository(pool), client)
    finally:
        await client.close()


async def get_athlete_id(request: Request) -> str:
    """Return the authenticated athlete ID from the session cookie."""
    import os
    dev_id = os.environ.get("DEV_ATHLETE_ID")
    if dev_id:
        return dev_id
    token = request.cookies.get("session")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    pool = get_pool()
    session_repo = PostgresSessionRepository(pool)
    session = await session_repo.get_by_token(token)
    if session is None:
        raise HTTPException(status_code=401, detail="Session expired")
    athlete = await PostgresStorage(pool).get(session.athlete_id)
    if athlete and athlete.is_blocked:
        raise HTTPException(status_code=403, detail="Account blocked")
    return session.athlete_id
