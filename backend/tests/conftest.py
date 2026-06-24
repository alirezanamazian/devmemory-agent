from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_qwen_client():
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock()
    client.embeddings = MagicMock()
    client.embeddings.create = AsyncMock()
    return client


@pytest.fixture
def mock_memory_engine():
    engine = MagicMock()
    engine.search_memories = AsyncMock(return_value=[])
    engine.save_memory = AsyncMock()
    engine.reinforce_memory = AsyncMock()
    engine.get_user_memories = AsyncMock(return_value=[])
    engine.get_stats = AsyncMock(return_value={})
    engine.forget_expired_memories = AsyncMock(return_value=0)
    engine.delete_memory = AsyncMock()
    return engine
