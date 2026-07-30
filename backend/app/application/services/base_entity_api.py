"""
Base Entity API
================
Base class for per-entity API layers with lifecycle hooks.
Moved from app/apis/ to application/services/ for clean architecture (BE#21).
"""
from typing import Any, Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import CurrentUser
from app.meta.registry import EntityMeta


@dataclass
class Context:
    db: AsyncSession
    user: CurrentUser
    meta: EntityMeta


class BaseEntityAPI:
    """Base class for per-entity API layers.
    
    Each entity implements hooks for validation and business logic.
    """
    
    async def validate_create(self, data: dict[str, Any], ctx: Context) -> Optional[dict[str, str]]:
        """Validate data before create. Return dict of field errors or None."""
        return None
    
    async def validate_update(self, id: str, data: dict[str, Any], ctx: Context) -> Optional[dict[str, str]]:
        """Validate data before update. Return dict of field errors or None."""
        return None
    
    async def before_create(self, data: dict[str, Any], ctx: Context) -> dict[str, Any]:
        """Hook before create. Can modify data."""
        return data
    
    async def after_create(self, record: Any, ctx: Context) -> None:
        """Hook after create."""
        pass
    
    async def before_update(self, record: Any, data: dict[str, Any], ctx: Context) -> dict[str, Any]:
        """Hook before update. Can modify data."""
        return data
    
    async def after_update(self, record: Any, ctx: Context) -> None:
        """Hook after update."""
        pass
    
    async def before_delete(self, record: Any, ctx: Context) -> None:
        """Hook before delete."""
        pass
    
    async def after_delete(self, ctx: Context) -> None:
        """Hook after delete."""
        pass
