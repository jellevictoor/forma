"""Tests for SQLiteChat adapter."""

import pytest

from forma.adapters.sqlite_chat import SQLiteChat


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture
def chat(db_path):
    return SQLiteChat(db_path)


async def test_list_messages_empty_when_no_messages(chat):
    result = await chat.list_messages("workout-1")

    assert result == []


async def test_append_and_list_single_message(chat):
    await chat.append_message("workout-1", "user", "How did I do?")

    result = await chat.list_messages("workout-1")

    assert len(result) == 1


async def test_message_has_correct_role(chat):
    await chat.append_message("workout-1", "user", "How did I do?")

    result = await chat.list_messages("workout-1")

    assert result[0].role == "user"


async def test_message_has_correct_content(chat):
    await chat.append_message("workout-1", "model", "Great run!")

    result = await chat.list_messages("workout-1")

    assert result[0].content == "Great run!"


async def test_messages_are_returned_in_order(chat):
    await chat.append_message("workout-1", "user", "First message")
    await chat.append_message("workout-1", "model", "First response")
    await chat.append_message("workout-1", "user", "Second message")

    result = await chat.list_messages("workout-1")

    assert result[0].content == "First message"
    assert result[1].content == "First response"
    assert result[2].content == "Second message"


async def test_messages_are_isolated_by_workout(chat):
    await chat.append_message("workout-1", "user", "Workout 1 message")
    await chat.append_message("workout-2", "user", "Workout 2 message")

    result = await chat.list_messages("workout-1")

    assert len(result) == 1
    assert result[0].content == "Workout 1 message"


async def test_clear_removes_all_messages(chat):
    await chat.append_message("workout-1", "user", "Message 1")
    await chat.append_message("workout-1", "model", "Response 1")
    await chat.clear_messages("workout-1")

    result = await chat.list_messages("workout-1")

    assert result == []


async def test_clear_only_removes_target_workout(chat):
    await chat.append_message("workout-1", "user", "Keep this")
    await chat.append_message("workout-2", "user", "Clear this")
    await chat.clear_messages("workout-2")

    result = await chat.list_messages("workout-1")

    assert len(result) == 1
