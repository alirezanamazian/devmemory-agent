import logging
from typing import List, Optional

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from app.container import Container
from app.core.memory_engine import MemoryEngine
from app.models.memory import MemoryResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/memories/{user_id}", response_model=List[MemoryResponse])
@inject
async def list_memories(
    user_id: str,
    project_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    engine: MemoryEngine = Depends(Provide[Container.memory_engine]),
) -> List[MemoryResponse]:
    return await engine.get_user_memories(user_id, project_id, limit)


@router.delete("/memories/{user_id}/{memory_id}")
@inject
async def delete_memory(
    user_id: str,
    memory_id: str,
    engine: MemoryEngine = Depends(Provide[Container.memory_engine]),
) -> dict:
    await engine.delete_memory(memory_id)
    return {"deleted": True, "memory_id": memory_id}


@router.post("/memories/{user_id}/forget")
@inject
async def run_decay_forget(
    user_id: str,
    engine: MemoryEngine = Depends(Provide[Container.memory_engine]),
) -> dict:
    """Run Ebbinghaus decay and auto-forget memories below importance threshold."""
    forgotten = await engine.forget_expired_memories(user_id)
    return {"user_id": user_id, "memories_forgotten": forgotten}


@router.get("/memories/{user_id}/stats")
@inject
async def memory_stats(
    user_id: str,
    project_id: Optional[str] = Query(None),
    engine: MemoryEngine = Depends(Provide[Container.memory_engine]),
) -> dict:
    return await engine.get_stats(user_id, project_id)
