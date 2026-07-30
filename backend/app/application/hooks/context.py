"""
Hook Context Objects
=====================
Dataclasses passed to entity lifecycle hooks.
"""
from typing import Any
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class SaveContext:
    """Context for before_save and after_save hooks."""
    db: AsyncSession
    user: Any
    entity: str
    action: str  # "create" or "update"
    meta: Any = None


@dataclass 
class WorkflowContext:
    """Context for workflow hooks."""
    db: AsyncSession
    user: Any
    entity: str
    doc: Any
    record_id: str
    action: str  # workflow action slug
    from_state: str
    to_state: str


# Alias for after_save hooks
HookContext = SaveContext

__all__ = ["SaveContext", "WorkflowContext", "HookContext"]
