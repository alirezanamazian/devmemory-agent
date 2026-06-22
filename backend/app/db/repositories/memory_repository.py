import logging
from typing import List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import MemoryCreate, MemoryResponse

logger = logging.getLogger(__name__)


class MemoryRepository:
    """
    Abstracts all DB operations for memories.
    MemoryEngine stays pure domain logic — no SQL leaks up.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _to_response(row: dict) -> MemoryResponse:
        # asyncpg returns id as uuid.UUID — MemoryResponse expects str
        return MemoryResponse(**{**row, "id": str(row["id"])})

    async def ensure_user_exists(self, user_id: str) -> None:
        """Upsert user row — memories FK on user_id."""
        await self.session.execute(
            text("""
                INSERT INTO users (user_id)
                VALUES (:user_id)
                ON CONFLICT (user_id) DO NOTHING
            """),
            {"user_id": user_id},
        )

    async def create(
        self,
        memory: MemoryCreate,
        embedding: List[float],
        decay_rate: float,
    ) -> MemoryResponse:
        memory_id = str(uuid4())
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"

        await self.ensure_user_exists(memory.user_id)

        result = await self.session.execute(
            text("""
                INSERT INTO memories
                    (id, user_id, project_id, session_id, content, memory_type,
                     importance_score, decay_rate, embedding)
                VALUES
                    (:id, :user_id, :project_id, :session_id, :content, :memory_type,
                     :importance_score, :decay_rate, :embedding)
                RETURNING id, user_id, project_id, content, summary, memory_type,
                          importance_score, decay_rate, access_count, created_at, last_accessed
            """),
            {
                "id": memory_id,
                "user_id": memory.user_id,
                "project_id": memory.project_id,
                "session_id": memory.session_id,
                "content": memory.content,
                "memory_type": memory.memory_type.value,
                "importance_score": memory.importance_score,
                "decay_rate": decay_rate,
                "embedding": embedding_str,
            },
        )
        row = result.mappings().one()
        return self._to_response(dict(row))

    async def find_by_vector(
        self,
        embedding: List[float],
        user_id: str,
        project_id: Optional[str] = None,
        limit: int = 20,
    ) -> List[Tuple[MemoryResponse, float]]:
        # pgvector ivfflat needs at least 1000 rows before it outperforms sequential scan;
        # for small datasets this still works correctly via seq scan fallback
        embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
        project_filter = "AND project_id = :project_id" if project_id else ""

        result = await self.session.execute(
            text(f"""
                SELECT id, user_id, project_id, content, summary, memory_type,
                       importance_score, decay_rate, access_count, created_at, last_accessed,
                       1 - (embedding <=> CAST(:embedding AS vector)) AS similarity
                FROM memories
                WHERE user_id = :user_id
                  AND importance_score > 0.0
                  {project_filter}
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
            """),
            {
                "embedding": embedding_str,
                "user_id": user_id,
                "project_id": project_id,
                "limit": limit,
            },
        )
        rows = result.mappings().all()
        out = []
        for row in rows:
            d = dict(row)
            similarity = d.pop("similarity")
            out.append((self._to_response(d), float(similarity)))
        return out

    async def update_access(self, memory_id: str) -> None:
        """Bump last_accessed + access_count atomically."""
        await self.session.execute(
            text("""
                UPDATE memories
                SET last_accessed = NOW(),
                    access_count = access_count + 1
                WHERE id = :id
            """),
            {"id": memory_id},
        )

    async def update_importance(self, memory_id: str, new_importance: float) -> None:
        await self.session.execute(
            text("UPDATE memories SET importance_score = :score WHERE id = :id"),
            {"score": new_importance, "id": memory_id},
        )

    async def delete_by_id(self, memory_id: str) -> None:
        await self.session.execute(
            text("DELETE FROM memories WHERE id = :id"),
            {"id": memory_id},
        )

    async def get_by_id(self, memory_id: str) -> Optional[MemoryResponse]:
        result = await self.session.execute(
            text("""
                SELECT id, user_id, project_id, content, summary, memory_type,
                       importance_score, decay_rate, access_count, created_at, last_accessed
                FROM memories WHERE id = :id
            """),
            {"id": memory_id},
        )
        row = result.mappings().one_or_none()
        return self._to_response(dict(row)) if row else None

    async def list_by_user(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MemoryResponse]:
        project_filter = "AND project_id = :project_id" if project_id else ""
        result = await self.session.execute(
            text(f"""
                SELECT id, user_id, project_id, content, summary, memory_type,
                       importance_score, decay_rate, access_count, created_at, last_accessed
                FROM memories
                WHERE user_id = :user_id {project_filter}
                ORDER BY importance_score DESC
                LIMIT :limit
            """),
            {"user_id": user_id, "project_id": project_id, "limit": limit},
        )
        return [self._to_response(dict(row)) for row in result.mappings().all()]

    async def get_stats(self, user_id: str, project_id: Optional[str] = None) -> dict:
        project_filter = "AND project_id = :project_id" if project_id else ""
        result = await self.session.execute(
            text(f"""
                SELECT
                    count(*) AS total_memories,
                    avg(importance_score) AS avg_importance,
                    min(created_at) AS oldest_memory,
                    max(created_at) AS newest_memory,
                    count(*) FILTER (WHERE importance_score < 0.2) AS memories_at_risk,
                    json_object_agg(memory_type, cnt) AS memories_by_type
                FROM (
                    SELECT importance_score, created_at, memory_type,
                           count(*) OVER (PARTITION BY memory_type) AS cnt
                    FROM memories
                    WHERE user_id = :user_id {project_filter}
                ) sub
            """),
            {"user_id": user_id, "project_id": project_id},
        )
        row = result.mappings().one()
        return dict(row)
