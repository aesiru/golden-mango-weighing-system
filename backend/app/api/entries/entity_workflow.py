"""
Entity Workflow Routes
=======================
Workflow transition operations for entities.
"""
import re
from typing import Any, Optional
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.core.serialization import record_to_dict
from app.meta.registry import MetaRegistry
from app.api.dependencies import get_workflow_progress_service, get_workflow_repo
from app.application.utils.doc_utils import format_state_label
from app.schemas.base import ActionResponse, WorkflowRequest
from app.infrastructure.database.repositories.workflow_repository import WorkflowRepository
from app.application.hooks.registry import hook_registry
from app.application.hooks.context import WorkflowContext
from app.application.services.notifications.socketio import socket_manager
from app.infrastructure.database.repositories.entity_repository import get_entity_model
from app.application.services.workflows.workflow_progress_service import WorkflowProgressService
from app.application.email_notifications.document_notify import notify_after_workflow_transition

router = APIRouter(tags=["entity"])

@router.get("/{entity}/{record_id}/workflow-progress")
async def get_workflow_progress(
    entity: str,
    record_id: str,
    workflow_progress_service: WorkflowProgressService = Depends(get_workflow_progress_service),
):
    try:
        data = await workflow_progress_service.get_progress(entity, record_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ActionResponse(
        status="success",
        message="Workflow progress retrieved successfully",
        data=data,
    )


@router.post("/{entity}/workflow")
async def workflow_action(
    entity: str,
    request: WorkflowRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    workflow_repo: WorkflowRepository = Depends(get_workflow_repo),
):
    """Execute a workflow transition."""
    meta = MetaRegistry.get(entity)
    if not meta:
        return ActionResponse(
            status="error",
            message=f"Entity '{entity}' not found",
            errors={"entity": f"Unknown entity: {entity}"}
        )

    model = get_entity_model(entity)
    if not model:
        return ActionResponse(
            status="error",
            message=f"Model for '{entity}' not found",
            errors={"model": f"No SQLAlchemy model registered for: {entity}"}
        )

    user = await get_current_user_from_token(authorization, db)

    workflow = await workflow_repo.get_workflow(entity)
    if not workflow:
        return ActionResponse(
            status="error",
            message=f"No workflow configured for entity '{entity}'",
            errors={"workflow": f"Create a workflow with target_entity='{entity}' first"}
        )

    result = await db.execute(select(model).where(model.id == request.id))
    doc = result.scalar_one_or_none()

    if not doc:
        return ActionResponse(
            status="error",
            message=f"Record '{request.id}' not found",
            errors={"id": f"No {meta.label} found with ID: {request.id}"}
        )

    # Get current state and normalize to slug format
    current_state_raw = getattr(doc, "workflow_state", None)
    if not current_state_raw:
        initial_link = next((sl for sl in workflow.state_links if sl.is_initial), None)
        current_state = initial_link.state.slug if initial_link else None
    else:
        current_state = current_state_raw.lower().strip()
        current_state = re.sub(r'[^a-z0-9\s_]', '', current_state)
        current_state = re.sub(r'\s+', '_', current_state)

    # Validate transition
    is_valid, target_state, error = await workflow_repo.validate_transition(
        entity, current_state, request.action, user
    )

    if not is_valid:
        return ActionResponse(
            status="error",
            message=error,
            errors={"action": f"Cannot perform '{request.action}' from state '{current_state}'"}
        )

    # Resolve human-readable action label for workflow hooks
    action_label = None
    for t in workflow.transitions:
        if t.action_ref.slug == request.action:
            action_label = t.action_ref.label
            break
    if not action_label:
        action_label = request.action  # fallback to slug

    # Run workflow hook (pass human-readable label as action)
    wf_ctx = WorkflowContext(
        db=db, user=user, entity=entity, doc=doc,
        record_id=request.id, action=action_label,
        from_state=current_state, to_state=target_state
    )
    hook_result = await hook_registry.execute_workflow(entity, wf_ctx)

    if hook_result["status"] == "error":
        # Rollback any partial writes from the hook before returning error
        await db.rollback()
        return ActionResponse(
            status="error",
            message=hook_result["message"],
            errors=hook_result.get("errors")
        )

    # Apply state transition on the parent doc
    setattr(doc, "workflow_state", target_state)
    await db.commit()
    await db.refresh(doc)

    doc_dict = record_to_dict(doc)
    if target_state:
        await notify_after_workflow_transition(db, entity, doc_dict, target_state)

    await socket_manager.emit_workflow(entity, doc_dict, request.action, current_state, target_state)

    # Build response — pass through redirect data if the hook created a new record
    response_data = doc_dict
    if hook_result.get("action") == "generate_id":
        response_data = {
            **doc_dict,
            "redirect_action": "generate_id",
            "redirect_path": hook_result.get("path"),
        }
    if hook_result.get("auto_closed"):
        response_data = {
            **doc_dict,
            "auto_closed": True,
            "parent_entity": hook_result.get("parent_entity"),
            "parent_id": hook_result.get("parent_id"),
        }

    return ActionResponse(
        status="success",
        message=f"Successfully transitioned from '{format_state_label(current_state)}' to '{format_state_label(target_state)}'",
        data=response_data
    )
