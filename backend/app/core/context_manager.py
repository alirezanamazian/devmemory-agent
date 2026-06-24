import logging
from typing import List

from app.config import settings
from app.models.memory import MemoryResponse, MemorySearchResult

logger = logging.getLogger(__name__)


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
                if token_cost > max_tokens:
                    # Logged at warning, not just skipped silently — a memory this
                    # large will never fit regardless of what else is in context.
                    logger.warning(
                        "Memory %s (~%d tokens) exceeds the entire context budget (%d) "
                        "and will always be skipped — consider summarizing it.",
                        result.memory.id, token_cost, max_tokens,
                    )
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
