"""Health check endpoints.

GET /api/v1/health - Readiness probe (checks DB, optionally Redis)
GET /api/v1/health/liveness - Liveness probe (simple 200 OK)
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

router = APIRouter()


class HealthResponse(BaseModel):
    """Response body for readiness health check."""

    status: str
    database: str
    queue: str


class LivenessResponse(BaseModel):
    """Response body for liveness check."""

    status: str


@router.get(
    "/health",
    response_model=HealthResponse,
)
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    """Readiness probe - checks database and queue connectivity."""
    db_status = "healthy"
    queue_status = "healthy"

    # Check database
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    # Check queue (Redis or in-memory)
    if settings.queue_mode == "memory":
        queue_status = "healthy (in-memory)"
    else:
        try:
            import redis.asyncio as aioredis
            redis_client = aioredis.from_url(settings.redis_url)
            await redis_client.ping()
            await redis_client.aclose()
        except Exception:
            queue_status = "unhealthy"

    overall = "healthy" if db_status == "healthy" else "unhealthy"

    return HealthResponse(
        status=overall,
        database=db_status,
        queue=queue_status,
    )


@router.get(
    "/health/liveness",
    response_model=LivenessResponse,
)
async def liveness_check() -> LivenessResponse:
    """Liveness probe - simple 200 OK."""
    return LivenessResponse(status="ok")
