import logging
from typing import Optional

from fastmcp import FastMCP

from app.container import Container
from app.models.memory import MemoryCreate, MemoryType

logger = logging.getLogger(__name__)
mcp = FastMCP("DevMemory Agent")

# FastMCP builds each tool's JSON schema from the full function signature via
# Pydantic, with no concept of a framework-injected param (unlike FastAPI's
# Depends). A `Provide[...]` default on an `engine: MemoryEngine` param makes
# Pydantic choke trying to schema-ize MemoryEngine itself. So we resolve
# straight from the container instead of injecting it as a parameter.
_container = Container()


@mcp.tool()
async def memory_save(
    user_id: str,
    content: str,
    memory_type: str = "general",
    importance_score: float = 0.5,
    project_id: Optional[str] = None,
) -> dict:
    """Save a memory to the DevMemory Agent's persistent store."""
    engine = _container.memory_engine()
    mem = MemoryCreate(
        user_id=user_id,
        content=content,
        memory_type=MemoryType(memory_type),
        importance_score=importance_score,
        project_id=project_id,
    )
    saved = await engine.save_memory(mem)
    return {"id": saved.id, "content": saved.content, "memory_type": saved.memory_type}


@mcp.tool()
async def memory_search(
    user_id: str,
    query: str,
    project_id: Optional[str] = None,
    top_k: int = 5,
) -> list:
    """Search memories semantically using two-stage retrieval (embedding + reranking)."""
    engine = _container.memory_engine()
    results = await engine.search_memories(query, user_id, project_id, top_k)
    return [
        {
            "content": r.memory.content,
            "memory_type": r.memory.memory_type,
            "importance_score": r.memory.importance_score,
            "similarity_score": r.similarity_score,
            "rerank_score": r.rerank_score,
        }
        for r in results
    ]


@mcp.tool()
async def memory_forget(
    user_id: str,
    memory_id: Optional[str] = None,
    run_decay: bool = False,
) -> dict:
    """
    Forget a specific memory by ID, or run decay to auto-forget expired memories.
    If run_decay=True, applies Ebbinghaus decay and removes low-importance memories.
    """
    engine = _container.memory_engine()
    if memory_id:
        await engine.delete_memory(memory_id)
        return {"forgotten": True, "memory_id": memory_id}
    if run_decay:
        count = await engine.forget_expired_memories(user_id)
        return {"forgotten_count": count, "decay_applied": True}
    return {"error": "Provide memory_id or set run_decay=True"}


@mcp.tool()
async def memory_stats(
    user_id: str,
    project_id: Optional[str] = None,
) -> dict:
    """
    Get memory statistics for a user:
    total_memories, memories_by_type, average_importance,
    oldest/newest memory, memories_at_risk (importance < 0.2)
    """
    engine = _container.memory_engine()
    return await engine.get_stats(user_id, project_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")
