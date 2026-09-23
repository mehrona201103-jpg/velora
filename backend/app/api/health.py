"""Health and readiness endpoints for Railway."""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health():
    """Liveness probe — always returns ok if process is alive."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    """Readiness probe — checks critical dependencies."""
    checks = {"database": False, "redis": False}

    # Database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False

    # Redis (optional)
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = True
    except Exception:
        checks["redis"] = False

    ready = checks["database"]  # Redis is optional for basic readiness
    return {
        "status": "ready" if ready else "not_ready",
        "checks": checks,
    }
