import logging

import httpx
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.config import settings
from app.db.database import AsyncSessionFactory

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check(response: Response):
    """
    Ping DB and Qwen API — judges need to verify the stack is live.
    Returns HTTP 503 when the DB is unreachable so container healthchecks
    (which check the status code, not the JSON body) actually catch it.
    """
    db_status = "disconnected"
    qwen_status = "unreachable"

    try:
        async with AsyncSessionFactory() as session:
            await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        logger.warning("DB health check failed: %s", e)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.QWEN_BASE_URL}/models",
                headers={"Authorization": f"Bearer {settings.QWEN_API_KEY}"},
            )
            if resp.status_code < 500:
                qwen_status = "reachable"
    except Exception as e:
        logger.warning("Qwen health check failed: %s", e)

    if db_status != "connected":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "db": db_status,
        "qwen": qwen_status,
    }
