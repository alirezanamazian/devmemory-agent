import logging
from typing import List

import httpx
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, client: AsyncOpenAI):
        self._client = client
        # Separate httpx client for rerank endpoint (not in OpenAI spec)
        self._http = httpx.AsyncClient(
            base_url=settings.QWEN_BASE_URL,
            headers={"Authorization": f"Bearer {settings.QWEN_API_KEY}"},
            timeout=30.0,
        )

    async def embed(self, text: str) -> List[float]:
        """Single-text embedding via text-embedding-v4 (1536 dims)."""
        try:
            response = await self._client.embeddings.create(
                model=settings.QWEN_EMBEDDING_MODEL,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error("Embedding request failed: %s", e)
            raise

    async def rerank(self, query: str, documents: List[str]) -> List[float]:
        """
        Two-stage retrieval: call qwen3-rerank to reorder candidates by semantic relevance.
        Falls back to uniform scores if the reranker is unavailable — degraded but not broken.
        """
        if not documents:
            return []

        try:
            resp = await self._http.post(
                "/rerank",
                json={
                    "model": settings.QWEN_RERANK_MODEL,
                    "query": query,
                    "documents": documents,
                    "return_documents": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()

            # Results come back as [{index, relevance_score}, ...], re-sort by index
            scores = [0.0] * len(documents)
            for result in data.get("results", []):
                scores[result["index"]] = result["relevance_score"]
            return scores
        except httpx.HTTPStatusError as e:
            logger.warning("Reranker returned HTTP %s, falling back to uniform scores", e.response.status_code)
            return [1.0 / len(documents)] * len(documents)
        except httpx.RequestError as e:
            logger.warning("Reranker request failed (%s), falling back to uniform scores", e)
            return [1.0 / len(documents)] * len(documents)
        except (KeyError, ValueError, TypeError) as e:
            logger.warning("Reranker returned unexpected payload (%s), falling back to uniform scores", e)
            return [1.0 / len(documents)] * len(documents)

    async def aclose(self) -> None:
        await self._http.aclose()
