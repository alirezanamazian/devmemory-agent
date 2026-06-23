from dependency_injector import containers, providers
from openai import AsyncOpenAI

from app.agent.agent import DevMemoryAgent
from app.agent.extractor import MemoryExtractor
from app.config import settings
from app.core.context_manager import ContextWindowManager
from app.core.decay import DecayEngine
from app.core.embedding import EmbeddingService
from app.core.memory_engine import MemoryEngine


class Container(containers.DeclarativeContainer):
    # Modules get added here as they're built (app.api.*, app.mcp.server) —
    # wire() will import each one, so listing a module that doesn't exist yet breaks startup.
    wiring_config = containers.WiringConfiguration(modules=[])

    qwen_client = providers.Singleton(
        AsyncOpenAI,
        api_key=settings.QWEN_API_KEY,
        base_url=settings.QWEN_BASE_URL,
    )

    embedding_service = providers.Singleton(
        EmbeddingService,
        client=qwen_client,
    )

    decay_engine = providers.Singleton(DecayEngine)

    context_manager = providers.Singleton(ContextWindowManager)

    memory_engine = providers.Factory(
        MemoryEngine,
        embedding_service=embedding_service,
        decay_engine=decay_engine,
        context_manager=context_manager,
    )

    extractor = providers.Factory(
        MemoryExtractor,
        client=qwen_client,
    )

    agent = providers.Factory(
        DevMemoryAgent,
        memory_engine=memory_engine,
        context_manager=context_manager,
        extractor=extractor,
        qwen_client=qwen_client,
    )
