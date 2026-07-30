"""
Audit Service
=============
Records entity changes with before/after snapshots.
"""
import json
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.framework.models.infrastructure import AuditLog
from app.core.serialization import record_to_dict


class AuditService:
    """Service for recording audit trail entries."""

    @staticmethod
    async def log_create(
        db: AsyncSession,
        entity_name: str,
        record_id: str,
        after: Any,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> None:
        after_dict = record_to_dict(after) if not isinstance(after, dict) else after
        entry = AuditLog(
            entity_name=entity_name,
            record_id=record_id,
            action="create",
            user_id=user_id,
            username=username,
            before_snapshot=None,
            after_snapshot=json.dumps(after_dict, default=str),
            changed_fields=json.dumps(list(after_dict.keys())),
        )
        db.add(entry)
        await db.flush()

    @staticmethod
    async def log_update(
        db: AsyncSession,
        entity_name: str,
        record_id: str,
        before: dict,
        after: Any,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> None:
        after_dict = record_to_dict(after) if not isinstance(after, dict) else after
        changed = [k for k in after_dict if before.get(k) != after_dict.get(k)]
        entry = AuditLog(
            entity_name=entity_name,
            record_id=record_id,
            action="update",
            user_id=user_id,
            username=username,
            before_snapshot=json.dumps(before, default=str),
            after_snapshot=json.dumps(after_dict, default=str),
            changed_fields=json.dumps(changed),
        )
        db.add(entry)
        await db.flush()

    @staticmethod
    async def log_delete(
        db: AsyncSession,
        entity_name: str,
        record_id: str,
        before: dict,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> None:
        entry = AuditLog(
            entity_name=entity_name,
            record_id=record_id,
            action="delete",
            user_id=user_id,
            username=username,
            before_snapshot=json.dumps(before, default=str),
            after_snapshot=None,
            changed_fields=None,
        )
        db.add(entry)
        await db.flush()

    @staticmethod
    async def log_workflow(
        db: AsyncSession,
        entity_name: str,
        record_id: str,
        from_state: str,
        to_state: str,
        action_slug: str,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
    ) -> None:
        entry = AuditLog(
            entity_name=entity_name,
            record_id=record_id,
            action="workflow",
            user_id=user_id,
            username=username,
            before_snapshot=json.dumps({"workflow_state": from_state}),
            after_snapshot=json.dumps({"workflow_state": to_state, "action": action_slug}),
            changed_fields=json.dumps(["workflow_state"]),
        )
        db.add(entry)
        await db.flush()


audit_service = AuditService()
