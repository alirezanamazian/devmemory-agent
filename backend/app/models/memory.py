from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    GENERAL = "general"
    PREFERENCE = "preference"
    DECISION = "decision"
    BUG_FIX = "bug_fix"
    PATTERN = "pattern"


class MemoryCreate(BaseModel):
    user_id: str
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    content: str = Field(min_length=1)
    memory_type: MemoryType = MemoryType.GENERAL
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)


class MemoryResponse(BaseModel):
    id: str
    user_id: str
    project_id: Optional[str] = None
    content: str
    summary: Optional[str] = None
    memory_type: str
    importance_score: float
    decay_rate: float
    access_count: int
    created_at: datetime
    last_accessed: datetime

    model_config = {"from_attributes": True}


class MemorySearchResult(BaseModel):
    memory: MemoryResponse
    similarity_score: float
    rerank_score: Optional[float] = None


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    user_id: str
    project_id: Optional[str] = None
    session_id: Optional[str] = None
    message: str = Field(min_length=1)


class ChatResponse(BaseModel):
    session_id: str
    response: str
    memories_used: List[MemoryResponse]
    memories_extracted: int


class WorkspaceContext(BaseModel):
    user_id: str
    project_id: Optional[str] = None
    workspace_id: Optional[str] = None  # future team/org tenancy

    @property
    def scope_key(self) -> str:
        """Unique scope key for memory isolation across users/workspaces/projects."""
        parts = [self.user_id]
        if self.workspace_id:
            parts.insert(0, self.workspace_id)
        if self.project_id:
            parts.append(self.project_id)
        return ":".join(parts)
