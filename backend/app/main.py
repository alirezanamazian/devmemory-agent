import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, health, memories
from app.container import Container
from app.db.database import init_db

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="DevMemory Agent",
    description="AI agent with persistent memory across developer sessions — built on Qwen Cloud",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

container = Container()
container.wire(modules=["app.api.chat", "app.api.memories"])
app.container = container

app.include_router(health.router, tags=["health"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(memories.router, prefix="/api/v1", tags=["memories"])


@app.on_event("startup")
async def startup():
    await init_db()
