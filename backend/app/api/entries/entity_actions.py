"""
Entity Document Actions Routes
================================
Server action execution on entity documents (Frappe-style).
Extracted from entity_crud.py for SRP compliance.
"""
from typing import Any, Optional
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_from_token
from app.meta.registry import MetaRegistry
from app.schemas.base import ActionResponse
from app.application.services.access_control.rbac_service import RBACAppService
from app.api.dependencies import get_rbac_service
from app.application.services.documents.server_actions import server_actions, ActionContext
from app.infrastructure.database.repositories.entity_repository import get_entity_model

router = APIRouter(tags=["entity"])


class DocumentActionRequest(BaseModel):
    payload: Optional[dict[str, Any]] = None


@router.post("/{entity}/{id}/action/{action_name}")
async def document_action(
    entity: str,
    id: str,
    action_name: str,
    body: Optional[DocumentActionRequest] = None,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Execute a server action on a document (Frappe-style).

    Accepts an optional JSON body with a `payload` dict that will be passed
    to the handler (e.g. serial numbers collected from a frontend modal).

    The handler method is responsible for all validation (including
    workflow state checks). The framework only checks entity existence,
    permissions, and record existence.
    """
    meta = MetaRegistry.get(entity)
    if not meta:
        return ActionResponse(status="error", message=f"Entity '{entity}' not found")

    user = await get_current_user_from_token(authorization, db)
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="update",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        return ActionResponse(status="error", message="Permission denied")

    model = get_entity_model(entity)
    if not model:
        return ActionResponse(status="error", message=f"Model for '{entity}' not found")

    from sqlalchemy import select
    result = await db.execute(select(model).where(model.id == id))
    doc = result.scalar_one_or_none()

    if not doc:
        return ActionResponse(status="error", message=f"Record '{id}' not found")

    # Delegate entirely to the registered server action handler.
    # The handler does its own validation (workflow state, business rules, etc.)
    action_ctx = ActionContext(
        db=db, user=user, entity_name=entity, record_id=id,
        params={"doc": doc, "payload": body.payload if body else None}
    )
    result = await server_actions.execute(entity, action_name, action_ctx)
    return ActionResponse(**result)
