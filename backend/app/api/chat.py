import logging

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from app.agent.agent import DevMemoryAgent
from app.container import Container
from app.models.memory import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
@inject
async def chat(
    request: ChatRequest,
    agent: DevMemoryAgent = Depends(Provide[Container.agent]),
) -> ChatResponse:
    """Send a message and get a memory-augmented response from DevMemory."""
    return await agent.chat(request)
