"""
Health Check Routes
===================
Production-critical readiness probes.

    GET /health          — overall status (DB + cache)
    GET /health/db       — database connectivity only
    GET /health/cache    — cache connectivity only
"""
from fastapi import APIRouter
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", name="health_check")
async def health():
    """Aggregate health: checks DB (and cache if configured)."""
    from app.core.database import async_session_maker

    db_ok = False
    db_info: str | None = None

    try:
        async with async_session_maker() as session:
            row = await session.execute(text("SELECT version()"))
            db_info = row.scalar()
            db_ok = True
    except Exception as exc:  # noqa: BLE001
        db_info = str(exc)

    overall = "healthy" if db_ok else "degraded"
    return {
        "status": overall,
        "checks": {
            "database": {"ok": db_ok, "detail": db_info},
        },
    }


@router.get("/db", name="health_db")
async def health_db():
    """Database-only connectivity probe."""
    from app.core.database import async_session_maker

    try:
        async with async_session_maker() as session:
            row = await session.execute(text("SELECT version()"))
            version = row.scalar()
        return {"ok": True, "version": version}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


@router.get("/cache", name="health_cache")
async def health_cache():
    """Cache connectivity probe (no-op if cache is not configured)."""
    try:
        from app.infrastructure.cache import get_cache  # type: ignore[import-untyped]

        cache = get_cache()
        await cache.ping()
        return {"ok": True}
    except ImportError:
        return {"ok": True, "detail": "cache not configured"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
