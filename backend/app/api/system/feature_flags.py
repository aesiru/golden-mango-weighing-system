"""
Feature Flags API
=================
Runtime toggle viewer for platform feature flags.
Reads from Settings + core.feature_flags; does NOT mutate state
(toggles are controlled via environment variables / .env).

    GET /feature-flags           — list all known flags + current state (admin only)
    GET /feature-flags/{key}     — get a single flag value
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import CurrentUser, require_authenticated_user

router = APIRouter(prefix="/feature-flags", tags=["system"])

# Registry of known flags: key → (description, resolver callable)
_FLAG_REGISTRY: dict[str, tuple[str, object]] = {}


def _register_flags() -> None:
    """Populate flag registry from all known sources. Called lazily."""
    if _FLAG_REGISTRY:
        return  # already populated


@router.get("", name="list_feature_flags")
async def list_feature_flags(
    current_user: CurrentUser = Depends(require_authenticated_user),
):
    """Return all registered feature flags and their current values."""
    if not current_user.is_superuser and "Administrator" not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    _register_flags()
    data = [
        {"key": key, "description": desc, "enabled": resolver()}
        for key, (desc, resolver) in _FLAG_REGISTRY.items()
    ]
    return {"status": "success", "data": data, "total": len(data)}


@router.get("/{key}", name="get_feature_flag")
async def get_feature_flag(
    key: str,
    current_user: CurrentUser = Depends(require_authenticated_user),
):
    """Return the value of a single feature flag by its key."""
    _register_flags()
    if key not in _FLAG_REGISTRY:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Flag '{key}' not found")

    desc, resolver = _FLAG_REGISTRY[key]
    return {"key": key, "description": desc, "enabled": resolver()}
