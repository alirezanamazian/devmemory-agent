import logging
from typing import List, Optional

from app.config import settings
from app.core.context_manager import ContextWindowManager
from app.core.decay import DecayEngine
from app.core.embedding import EmbeddingService
from app.db.database import get_db
from app.db.repositories.memory_repository import MemoryRepository
from app.models.memory import MemoryCreate, MemoryResponse, MemorySearchResult

logger = logging.getLogger(__name__)


class MemoryEngine:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        decay_engine: DecayEngine,
        context_manager: ContextWindowManager,
    ):
        self._embed = embedding_service
        self._decay = decay_engine
        self._ctx = context_manager

    async def save_memory(self, memory: MemoryCreate) -> MemoryResponse:
        """Embed content, set decay rate by type, store in pgvector."""
        embedding = await self._embed.embed(memory.content)
        decay_rate = self._decay.calculate_decay_rate_for_type(memory.memory_type.value)

        async with get_db() as session:
            repo = MemoryRepository(session)
            return await repo.create(memory, embedding, decay_rate)

    async def search_memories(
        self,
        query: str,
        user_id: str,
        project_id: Optional[str] = None,
        top_k: int = settings.MEMORY_TOP_K,
    ) -> List[MemorySearchResult]:
        """
        Two-stage retrieval:
        1. pgvector cosine similarity → top 20 candidates
        2. qwen3-rerank → reorder by semantic relevance → top_k
        Decay applied per-result so stale memories get penalized even if similar.
        """
        query_embedding = await self._embed.embed(query)

        async with get_db() as session:
            repo = MemoryRepository(session)
            candidates = await repo.find_by_vector(query_embedding, user_id, project_id, limit=20)

        if not candidates:
            return []

        documents = [mem.content for mem, _ in candidates]
        rerank_scores = await self._embed.rerank(query, documents)

        results: List[MemorySearchResult] = []
        for (memory, similarity), rerank_score in zip(candidates, rerank_scores):
            # Apply decay before scoring — a stale memory may still be similar but should rank lower
            current_importance = self._decay.calculate_current_importance(
                memory.importance_score,
                memory.decay_rate,
                memory.last_accessed,
                memory.access_count,
            )
            memory.importance_score = current_importance
            results.append(
                MemorySearchResult(
                    memory=memory,
                    similarity_score=similarity,
                    rerank_score=rerank_score,
                )
            )

        results.sort(
            key=lambda r: (r.rerank_score or r.similarity_score) * r.memory.importance_score,
            reverse=True,
        )
        return results[:top_k]

    async def forget_expired_memories(self, user_id: str) -> int:
        """Apply Ebbinghaus decay to all user memories; delete those below threshold."""
        async with get_db() as session:
            repo = MemoryRepository(session)
            all_memories = await repo.list_by_user(user_id, limit=10000)

            forgotten = 0
            for mem in all_memories:
                current = self._decay.calculate_current_importance(
                    mem.importance_score,
                    mem.decay_rate,
                    mem.last_accessed,
                    mem.access_count,
                )
                if self._decay.should_forget(current):
                    await repo.delete_by_id(mem.id)
                    forgotten += 1
                elif abs(current - mem.importance_score) > 0.001:
                    await repo.update_importance(mem.id, current)

        logger.info("Forgot %d expired memories for user %s", forgotten, user_id)
        return forgotten

    async def reinforce_memory(self, memory_id: str) -> Optional[MemoryResponse]:
        """Called when a memory is used — boosts importance, updates access tracking."""
        async with get_db() as session:
            repo = MemoryRepository(session)
            mem = await repo.get_by_id(memory_id)
            if not mem:
                return None
            new_importance = self._decay.boost_importance(mem.importance_score)
            await repo.update_importance(memory_id, new_importance)
            await repo.update_access(memory_id)
            mem.importance_score = new_importance
            return mem

    async def get_user_memories(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MemoryResponse]:
        async with get_db() as session:
            repo = MemoryRepository(session)
            return await repo.list_by_user(user_id, project_id, limit)

    async def delete_memory(self, memory_id: str) -> None:
        async with get_db() as session:
            repo = MemoryRepository(session)
            await repo.delete_by_id(memory_id)

    async def get_stats(self, user_id: str, project_id: Optional[str] = None) -> dict:
        async with get_db() as session:
            repo = MemoryRepository(session)
            return await repo.get_stats(user_id, project_id)
