"""
Version Route
=============
Exposes build metadata for deployment verification.

    GET /version   — returns name, version, environment
"""
from fastapi import APIRouter

router = APIRouter(prefix="/version", tags=["system"])


@router.get("", name="version_info")
async def version():
    """Return application version and runtime environment."""
    from app.core.config import settings

    env = getattr(settings, "ENVIRONMENT", "production")
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": env,
    }
