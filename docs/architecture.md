# DevMemory Agent — System Architecture

## Request Flow

```mermaid
flowchart LR
    Dev[Developer / IDE] -->|MCP Protocol| MCP[MCP Server]
    Dev -->|REST API| API[FastAPI Backend]
    MCP --> Agent[DevMemory Agent]
    API --> Agent

    Agent --> QwenMax[qwen3.7-max<br/>Reasoning]
    Agent --> Embed[text-embedding-v4<br/>Embedding]
    Agent --> Rerank[qwen3-rerank<br/>Reranking]

    Agent --> MemEngine[Memory Engine]
    MemEngine --> Decay[Ebbinghaus<br/>Decay Engine]
    MemEngine --> CtxMgr[Context Window<br/>Manager]
    MemEngine --> Repo[Memory Repository]

    Repo --> PG[(PostgreSQL<br/>+ pgvector<br/>Alibaba Cloud RDS)]
    Agent --> Redis[(Redis<br/>Session Cache)]

    subgraph QwenCloud[Qwen Cloud — Alibaba Cloud]
        QwenMax
        Embed
        Rerank
    end
```

## Memory Lifecycle

```mermaid
flowchart TD
    Input[User Message] --> Search[Vector Search<br/>top-20 candidates]
    Search --> Rerank2[Rerank by relevance]
    Rerank2 --> CtxFit[Fit in 8k context window]
    CtxFit --> Inject[Inject into system prompt]
    Inject --> Qwen[qwen3.7-max generates response]
    Qwen --> Extract[Extract new memories]
    Extract --> Save[Save + embed]
    Save --> Reinforce[Reinforce used memories]
    Reinforce --> Decay2[Decay job: /memories/user/forget]
    Decay2 --> Forget{importance < 0.05?}
    Forget -->|Yes| Delete[Auto-forget]
    Forget -->|No| Keep[Keep + update score]
```

## Component Responsibilities

| Component | File | Responsibility |
|---|---|---|
| `DevMemoryAgent` | `app/agent/agent.py` | Full chat loop: retrieve → select → inject → call Qwen with tools → dispatch tool calls → extract → save → reinforce |
| `MemoryEngine` | `app/core/memory_engine.py` | Orchestrates two-stage retrieval (vector + rerank), decay-aware scoring, save/forget/reinforce |
| `MemoryRepository` | `app/db/repositories/memory_repository.py` | All raw SQL — pgvector cosine search, CRUD, stats. No SQL leaks above this layer |
| `DecayEngine` | `app/core/decay.py` | Ebbinghaus forgetting curve with access-count retention bonus, per-type decay rates |
| `EmbeddingService` | `app/core/embedding.py` | `text-embedding-v4` embeddings + `qwen3-rerank` reranking, with graceful fallback |
| `ContextWindowManager` | `app/core/context_manager.py` | Greedy token-budget selection for the 8k memory context window |
| `MemoryExtractor` | `app/agent/extractor.py` | Autonomous LLM-based memory extraction from each conversation turn |
| `Container` | `app/container.py` | dependency-injector wiring for every service above |
| MCP Server | `app/mcp/server.py` | 4 tools (`memory_save`, `memory_search`, `memory_forget`, `memory_stats`) for any MCP-compatible IDE/agent |
