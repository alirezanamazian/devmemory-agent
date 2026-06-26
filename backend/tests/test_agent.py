from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.agent.agent import DevMemoryAgent
from app.agent.extractor import MemoryExtractor
from app.core.context_manager import ContextWindowManager
from app.models.memory import ChatRequest, MemoryResponse, MemorySearchResult


def _completion(content, tool_calls=None, finish_reason="stop"):
    completion = MagicMock()
    completion.choices = [MagicMock()]
    completion.choices[0].finish_reason = finish_reason
    completion.choices[0].message.content = content
    completion.choices[0].message.tool_calls = tool_calls
    return completion


@pytest.mark.asyncio
async def test_chat_returns_response(mock_qwen_client, mock_memory_engine):
    ctx = ContextWindowManager()
    extractor = MemoryExtractor(mock_qwen_client)
    extractor.extract_memories = AsyncMock(return_value=[])

    mock_qwen_client.chat.completions.create = AsyncMock(
        return_value=_completion("Here is your answer.")
    )

    agent = DevMemoryAgent(mock_memory_engine, ctx, extractor, mock_qwen_client)
    request = ChatRequest(user_id="test_user", message="How do I use asyncpg?")

    response = await agent.chat(request)
    await agent.last_extraction_task

    assert response.response == "Here is your answer."
    assert isinstance(response.session_id, str)
    assert response.memories_extracted == 0


@pytest.mark.asyncio
async def test_chat_uses_retrieved_memories(mock_qwen_client, mock_memory_engine):
    ctx = ContextWindowManager()
    extractor = MemoryExtractor(mock_qwen_client)
    extractor.extract_memories = AsyncMock(return_value=[])

    fake_memory = MemoryResponse(
        id=str(uuid4()),
        user_id="test_user",
        content="User prefers asyncpg over psycopg2",
        memory_type="preference",
        importance_score=0.8,
        decay_rate=0.02,
        access_count=3,
        created_at=datetime.now(timezone.utc),
        last_accessed=datetime.now(timezone.utc),
    )
    mock_memory_engine.search_memories = AsyncMock(
        return_value=[MemorySearchResult(memory=fake_memory, similarity_score=0.9, rerank_score=0.95)]
    )
    mock_qwen_client.chat.completions.create = AsyncMock(
        return_value=_completion("Based on your preference for asyncpg...")
    )

    agent = DevMemoryAgent(mock_memory_engine, ctx, extractor, mock_qwen_client)
    request = ChatRequest(user_id="test_user", message="How should I connect to Postgres?")

    response = await agent.chat(request)
    await agent.last_extraction_task

    assert len(response.memories_used) == 1
    assert response.memories_used[0].content == "User prefers asyncpg over psycopg2"
    mock_memory_engine.reinforce_memory.assert_called()


@pytest.mark.asyncio
async def test_chat_dispatches_tool_call(mock_qwen_client, mock_memory_engine):
    ctx = ContextWindowManager()
    extractor = MemoryExtractor(mock_qwen_client)
    extractor.extract_memories = AsyncMock(return_value=[])

    saved_memory = MemoryResponse(
        id=str(uuid4()),
        user_id="test_user",
        content="use asyncpg",
        memory_type="decision",
        importance_score=0.7,
        decay_rate=0.05,
        access_count=0,
        created_at=datetime.now(timezone.utc),
        last_accessed=datetime.now(timezone.utc),
    )
    mock_memory_engine.save_memory = AsyncMock(return_value=saved_memory)

    tool_call = MagicMock()
    tool_call.id = "call_123"
    tool_call.function.name = "save_developer_insight"
    tool_call.function.arguments = (
        '{"insight": "use asyncpg", "memory_type": "decision", "importance": 0.7}'
    )

    first = _completion(None, tool_calls=[tool_call], finish_reason="tool_calls")
    first.choices[0].message.model_dump.return_value = {"role": "assistant", "tool_calls": [{"id": "call_123"}]}
    second = _completion("Saved your decision about asyncpg.")

    mock_qwen_client.chat.completions.create = AsyncMock(side_effect=[first, second])

    agent = DevMemoryAgent(mock_memory_engine, ctx, extractor, mock_qwen_client)
    request = ChatRequest(user_id="test_user", message="Remember that I decided to use asyncpg")

    response = await agent.chat(request)

    assert response.response == "Saved your decision about asyncpg."
    mock_memory_engine.save_memory.assert_called_once()


@pytest.mark.asyncio
async def test_chat_extracts_and_saves_new_memories(mock_qwen_client, mock_memory_engine):
    ctx = ContextWindowManager()
    extractor = MemoryExtractor(mock_qwen_client)

    from app.models.memory import MemoryCreate, MemoryType

    extractor.extract_memories = AsyncMock(
        return_value=[
            MemoryCreate(user_id="test_user", content="likes asyncpg", memory_type=MemoryType.PREFERENCE)
        ]
    )
    mock_qwen_client.chat.completions.create = AsyncMock(return_value=_completion("Noted."))

    agent = DevMemoryAgent(mock_memory_engine, ctx, extractor, mock_qwen_client)
    request = ChatRequest(user_id="test_user", message="I like asyncpg")

    response = await agent.chat(request)
    await agent.last_extraction_task

    assert response.memories_extracted == 0  # extraction is async now
    mock_memory_engine.save_memory.assert_called_once()


@pytest.mark.asyncio
async def test_chat_continues_when_save_memory_fails(mock_qwen_client, mock_memory_engine):
    ctx = ContextWindowManager()
    extractor = MemoryExtractor(mock_qwen_client)

    from app.models.memory import MemoryCreate, MemoryType

    extractor.extract_memories = AsyncMock(
        return_value=[MemoryCreate(user_id="test_user", content="x", memory_type=MemoryType.GENERAL)]
    )
    mock_memory_engine.save_memory = AsyncMock(side_effect=RuntimeError("db down"))
    mock_qwen_client.chat.completions.create = AsyncMock(return_value=_completion("Still answered."))

    agent = DevMemoryAgent(mock_memory_engine, ctx, extractor, mock_qwen_client)
    request = ChatRequest(user_id="test_user", message="hello")

    response = await agent.chat(request)
    await agent.last_extraction_task

    assert response.response == "Still answered."
    assert response.memories_extracted == 0
    mock_memory_engine.save_memory.assert_called_once()


@pytest.mark.asyncio
async def test_extract_memories_skips_qwen_call_for_empty_conversation(mock_qwen_client):
    extractor = MemoryExtractor(mock_qwen_client)

    result = await extractor.extract_memories([], "test_user")

    assert result == []
    mock_qwen_client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_chat_retries_then_falls_back_on_empty_completion(mock_qwen_client, mock_memory_engine):
    ctx = ContextWindowManager()
    extractor = MemoryExtractor(mock_qwen_client)
    extractor.extract_memories = AsyncMock(return_value=[])

    # Qwen sometimes returns an empty completion with no tool call and no
    # error — the agent should retry once, then fall back to a non-empty
    # message rather than showing the user a blank response.
    mock_qwen_client.chat.completions.create = AsyncMock(
        side_effect=[_completion(""), _completion("")]
    )

    agent = DevMemoryAgent(mock_memory_engine, ctx, extractor, mock_qwen_client)
    request = ChatRequest(user_id="test_user", message="hello")

    response = await agent.chat(request)
    await agent.last_extraction_task

    assert response.response == "Got it — noted."
    assert mock_qwen_client.chat.completions.create.call_count == 2


@pytest.mark.asyncio
async def test_chat_uses_retry_result_when_first_completion_is_empty(mock_qwen_client, mock_memory_engine):
    ctx = ContextWindowManager()
    extractor = MemoryExtractor(mock_qwen_client)
    extractor.extract_memories = AsyncMock(return_value=[])

    mock_qwen_client.chat.completions.create = AsyncMock(
        side_effect=[_completion(""), _completion("Second try worked.")]
    )

    agent = DevMemoryAgent(mock_memory_engine, ctx, extractor, mock_qwen_client)
    request = ChatRequest(user_id="test_user", message="hello")

    response = await agent.chat(request)
    await agent.last_extraction_task

    assert response.response == "Second try worked."
