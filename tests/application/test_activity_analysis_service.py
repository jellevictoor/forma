"""Tests for ActivityAnalysisService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from forma.application.activity_analysis_service import ActivityAnalysisService
from forma.domain.athlete import Athlete, Goal, GoalType
from forma.domain.workout import Workout, WorkoutType
from forma.ports.activity_analysis_repository import (
    ActivityAnalysis,
    CachedActivityAnalysis,
)


def _make_workout(
    workout_id="w1",
    workout_type=WorkoutType.RUN,
    days_ago=1,
    duration_seconds=3600,
    distance_meters=10000.0,
    average_heartrate=150.0,
):
    start = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    return Workout(
        id=workout_id,
        athlete_id="athlete1",
        workout_type=workout_type,
        name="Morning run",
        start_time=start,
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        average_heartrate=average_heartrate,
    )


def _make_athlete():
    return Athlete(
        id="athlete1",
        name="Test Athlete",
        goals=[Goal(goal_type=GoalType.RACE, description="Sub-50 10k")],
    )


def _sample_analysis(**overrides):
    defaults = dict(
        performance_assessment="Solid tempo run.",
        training_load_context="You were fresh going in.",
        goal_relevance="Directly supports your 10k goal.",
        comparison_to_recent="Faster than your last 3 runs.",
        takeaway="Keep this intensity for mid-week sessions.",
    )
    defaults.update(overrides)
    return ActivityAnalysis(**defaults)


def _make_deps():
    workout_repo = AsyncMock()
    workout_repo.get_workout = AsyncMock(return_value=_make_workout())
    workout_repo.list_workouts_for_athlete = AsyncMock(return_value=[])

    analytics_repo = AsyncMock()
    analytics_repo.daily_effort = AsyncMock(return_value=[])

    athlete_repo = AsyncMock()
    athlete_repo.get = AsyncMock(return_value=_make_athlete())

    cache_repo = AsyncMock()
    cache_repo.get = AsyncMock(return_value=None)
    cache_repo.save = AsyncMock()

    chat_repo = AsyncMock()
    chat_repo.list_messages = AsyncMock(return_value=[])
    chat_repo.append_message = AsyncMock()

    return workout_repo, analytics_repo, athlete_repo, cache_repo, chat_repo


def _make_service(workout_repo=None, analytics_repo=None, athlete_repo=None, cache_repo=None, chat_repo=None):
    wr, ar, atr, cr, chr_ = _make_deps()
    return ActivityAnalysisService(
        workout_repo=workout_repo or wr,
        analytics_repo=analytics_repo or ar,
        athlete_repo=athlete_repo or atr,
        cache_repo=cache_repo or cr,
        chat_repo=chat_repo or chr_,
    )


async def test_get_cached_returns_none_when_no_cache():
    service = _make_service()

    result = await service.get_cached("w1")

    assert result is None


async def test_get_cached_returns_cached_analysis():
    _, _, _, cache_repo, _ = _make_deps()
    cached = CachedActivityAnalysis(
        workout_id="w1",
        analysis=_sample_analysis(),
        generated_at=datetime.now(tz=timezone.utc),
    )
    cache_repo.get = AsyncMock(return_value=cached)
    service = _make_service(cache_repo=cache_repo)

    result = await service.get_cached("w1")

    assert result is cached


async def test_get_cached_does_not_call_llm():
    service = _make_service()

    with patch.object(service, "_call_llm") as mock_gemini:
        await service.get_cached("w1")

    mock_gemini.assert_not_called()


async def test_generate_and_cache_returns_cached_analysis():
    service = _make_service()

    with patch.object(service, "_call_llm", return_value=_sample_analysis()):
        result = await service.generate_and_cache("athlete1", "w1")

    assert isinstance(result, CachedActivityAnalysis)


async def test_generate_and_cache_saves_to_cache():
    _, _, _, cache_repo, _ = _make_deps()
    service = _make_service(cache_repo=cache_repo)

    with patch.object(service, "_call_llm", return_value=_sample_analysis()):
        await service.generate_and_cache("athlete1", "w1")

    cache_repo.save.assert_called_once()


async def test_generate_and_cache_calls_gemini():
    service = _make_service()

    with patch.object(service, "_call_llm", return_value=_sample_analysis()) as mock_gemini:
        await service.generate_and_cache("athlete1", "w1")

    mock_gemini.assert_called_once()


async def test_generate_raises_when_workout_not_found():
    workout_repo, _, _, _, _ = _make_deps()
    workout_repo.get_workout = AsyncMock(return_value=None)
    service = _make_service(workout_repo=workout_repo)

    with pytest.raises(ValueError, match="not found"):
        with patch.object(service, "_call_llm", return_value=_sample_analysis()):
            await service.generate_and_cache("athlete1", "w1")


async def test_generate_fetches_athlete_profile():
    _, _, athlete_repo, _, _ = _make_deps()
    service = _make_service(athlete_repo=athlete_repo)

    with patch.object(service, "_call_llm", return_value=_sample_analysis()):
        await service.generate_and_cache("athlete1", "w1")

    athlete_repo.get.assert_called_once_with("athlete1")


async def test_prompt_contains_workout_type():
    service = _make_service()

    with patch.object(service, "_call_llm", return_value=_sample_analysis()) as mock:
        await service.generate_and_cache("athlete1", "w1")

    prompt = mock.call_args[0][0]
    assert "run" in prompt.lower()


async def test_prompt_contains_athlete_goals():
    service = _make_service()

    with patch.object(service, "_call_llm", return_value=_sample_analysis()) as mock:
        await service.generate_and_cache("athlete1", "w1")

    prompt = mock.call_args[0][0]
    assert "Sub-50 10k" in prompt


async def test_prompt_contains_fitness_state():
    service = _make_service()

    with patch.object(service, "_call_llm", return_value=_sample_analysis()) as mock:
        await service.generate_and_cache("athlete1", "w1")

    prompt = mock.call_args[0][0]
    assert "Fitness" in prompt


async def test_prompt_includes_recent_similar_workouts():
    workout_repo, _, _, _, _ = _make_deps()
    recent_run = _make_workout(workout_id="w2", days_ago=5, distance_meters=8000.0)
    workout_repo.list_workouts_for_athlete = AsyncMock(return_value=[recent_run])
    service = _make_service(workout_repo=workout_repo)

    with patch.object(service, "_call_llm", return_value=_sample_analysis()) as mock:
        await service.generate_and_cache("athlete1", "w1")

    prompt = mock.call_args[0][0]
    assert "8.0km" in prompt


async def test_prompt_handles_no_recent_similar_workouts():
    service = _make_service()

    with patch.object(service, "_call_llm", return_value=_sample_analysis()) as mock:
        await service.generate_and_cache("athlete1", "w1")

    prompt = mock.call_args[0][0]
    assert "No previous" in prompt


async def test_parse_response_handles_valid_json():
    service = _make_service()
    raw = '{"performance_assessment":"Good.","training_load_context":"Fresh.","goal_relevance":"On track.","comparison_to_recent":"Faster.","takeaway":"Keep it up."}'

    result = service._parse_response(raw)

    assert result.performance_assessment == "Good."


async def test_parse_response_strips_markdown_fences():
    service = _make_service()
    raw = '```json\n{"performance_assessment":"Good.","training_load_context":"Fresh.","goal_relevance":"On track.","comparison_to_recent":"Faster.","takeaway":"Keep it up."}\n```'

    result = service._parse_response(raw)

    assert result.performance_assessment == "Good."


async def test_parse_response_returns_fallback_on_invalid_json():
    service = _make_service()

    result = service._parse_response("not json at all")

    assert result.performance_assessment != ""


async def test_get_chat_messages_returns_empty_list_initially():
    service = _make_service()

    result = await service.get_chat_messages("w1")

    assert result == []


async def test_chat_saves_user_message():
    _, _, _, _, chat_repo = _make_deps()
    service = _make_service(chat_repo=chat_repo)

    with patch.object(service, "_call_llm_chat", return_value="Great run!"):
        await service.chat("athlete1", "w1", "How did I do?")

    chat_repo.append_message.assert_any_call("w1", "user", "How did I do?")


async def test_chat_saves_model_response():
    _, _, _, _, chat_repo = _make_deps()
    service = _make_service(chat_repo=chat_repo)

    with patch.object(service, "_call_llm_chat", return_value="Great run!"):
        await service.chat("athlete1", "w1", "How did I do?")

    chat_repo.append_message.assert_any_call("w1", "model", "Great run!")


async def test_chat_returns_model_response():
    service = _make_service()

    with patch.object(service, "_call_llm_chat", return_value="Solid tempo effort."):
        result = await service.chat("athlete1", "w1", "How was my pace?")

    assert result == "Solid tempo effort."


async def test_chat_raises_when_workout_not_found():
    workout_repo, _, _, _, _ = _make_deps()
    workout_repo.get_workout = AsyncMock(return_value=None)
    service = _make_service(workout_repo=workout_repo)

    with pytest.raises(ValueError, match="not found"):
        await service.chat("athlete1", "w1", "How did I do?")


async def test_chat_passes_history_to_gemini():
    from forma.ports.chat_repository import ChatMessage
    from datetime import timezone
    _, _, _, _, chat_repo = _make_deps()
    history = [ChatMessage(role="user", content="Prior question", created_at=datetime.now(tz=timezone.utc))]
    chat_repo.list_messages = AsyncMock(return_value=history)
    service = _make_service(chat_repo=chat_repo)

    with patch.object(service, "_call_llm_chat", return_value="Answer") as mock:
        await service.chat("athlete1", "w1", "New question")

    _, passed_history, *_ = mock.call_args[0]
    assert len(passed_history) == 1
    assert passed_history[0].content == "Prior question"
