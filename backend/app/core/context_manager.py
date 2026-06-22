from typing import List

from app.config import settings
from app.models.memory import MemoryResponse, MemorySearchResult


class ContextWindowManager:
    # ~4 chars per token — rough but consistent with GPT-family tokenizers
    CHARS_PER_TOKEN = 4

    async def select_memories(
        self,
        memories: List[MemorySearchResult],
        max_tokens: int = settings.MEMORY_CONTEXT_MAX_TOKENS,
    ) -> List[MemoryResponse]:
        """
        Greedy token-budget selection ranked by combined relevance + importance.
        Rerank score is the primary signal; importance_score breaks ties and
        penalizes stale memories even if they're semantically similar.
        """
        token_budget_remaining = max_tokens

        def combined_score(result: MemorySearchResult) -> float:
            rerank = result.rerank_score if result.rerank_score is not None else result.similarity_score
            return rerank * result.memory.importance_score

        ranked = sorted(memories, key=combined_score, reverse=True)

        selected: List[MemoryResponse] = []
        for result in ranked:
            token_cost = len(result.memory.content) // self.CHARS_PER_TOKEN
            if token_cost > token_budget_remaining:
                continue
            selected.append(result.memory)
            token_budget_remaining -= token_cost

        return selected

    def format_memories_for_prompt(self, memories: List[MemoryResponse]) -> str:
        """Format memories as a numbered list for system prompt injection."""
        if not memories:
            return ""
        lines = []
        for i, mem in enumerate(memories, 1):
            type_tag = f"[{mem.memory_type}]"
            lines.append(f"{i}. {type_tag} {mem.content}")
        return "\n".join(lines)
