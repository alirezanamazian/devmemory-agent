import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.container import Container

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
app.container = container

# Routers (app.api.*) and the MCP server get wired into the container
# once they exist — see container.wiring_config.
