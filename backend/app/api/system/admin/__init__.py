"""
Admin Router Package
====================
Modular admin endpoints split into focused sub-routers.
"""
from fastapi import APIRouter

from . import users, roles, permissions, ordering, model_editor, sessions, api_keys

router = APIRouter(prefix="/admin", tags=["admin"])

# Include all sub-routers
router.include_router(users.router)
router.include_router(roles.router)
router.include_router(permissions.router)
router.include_router(ordering.router)
router.include_router(model_editor.router)
router.include_router(sessions.router)
router.include_router(api_keys.router)
