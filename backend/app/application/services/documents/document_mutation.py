"""
Document Mutation Service
=========================
Write operations for documents (SRP: mutations only).

Provides:
- new_doc: Create a new document instance (not saved)
- save_doc: Save a document (insert or update)
- insert_doc: Insert a new document
- delete_doc: Delete a document
- apply_workflow_state: Validate and apply a workflow transition
"""
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.documents.document_service import DocumentAppService
from app.application.services.documents.naming_service import NamingAppService
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.infrastructure.database.repositories.naming_repository import NamingRepository
from app.application.services.documents.document_query import _get_model, get_meta, _record_to_dict


# =============================================================================
# new_doc
# =============================================================================

async def new_doc(
    entity: str,
    db: AsyncSession,
    **kwargs
) -> Optional[Any]:
    """Create a new document instance (not saved to database yet)."""
    model = _get_model(entity)
    if not model:
        return None

    meta = get_meta(entity)

    # Generate ID if naming is enabled and no ID provided
    if meta and meta.naming and meta.naming.enabled and "id" not in kwargs:
        naming_repo = NamingRepository(db)
        naming_service = NamingAppService(naming_repo)
        generated_id = await naming_service.generate_id(meta.naming, entity)
        if generated_id:
            kwargs["id"] = generated_id

    # Set initial workflow state if workflow enabled and no state provided
    if (meta and meta.workflow and meta.workflow.enabled and
        meta.workflow.state_field and meta.workflow.initial_state and
        meta.workflow.state_field not in kwargs):
        kwargs[meta.workflow.state_field] = meta.workflow.initial_state

    doc = model(**kwargs)
    return doc


# =============================================================================
# save_doc
# =============================================================================

async def save_doc(
    doc: Any,
    db: AsyncSession,
    commit: bool = True
) -> Any:
    """Save a document to the database (insert or update)."""
    from sqlalchemy import inspect

    from app.application.email_notifications.document_notify import (
        notify_after_document_insert,
    )

    insp = inspect(doc)
    was_insert = insp.transient
    if insp.transient:
        db.add(doc)

    if commit:
        await db.commit()
        await db.refresh(doc)
    else:
        await db.flush()

    if was_insert:
        await notify_after_document_insert(db, doc)

    return doc


# =============================================================================
# insert_doc
# =============================================================================

async def insert_doc(
    doc: Any,
    db: AsyncSession,
    commit: bool = True
) -> Any:
    """Insert a new document."""
    from app.application.email_notifications.document_notify import (
        notify_after_document_insert,
    )

    db.add(doc)
    if commit:
        await db.commit()
        await db.refresh(doc)
    else:
        await db.flush()
    await notify_after_document_insert(db, doc)
    return doc


# =============================================================================
# delete_doc
# =============================================================================

async def delete_doc(
    entity: str,
    id: str,
    db: AsyncSession,
    commit: bool = True
) -> bool:
    """Delete a document by entity name and ID."""
    document_repo = DocumentRepository(db)
    document_service = DocumentAppService(document_repo)
    doc = await document_service.get_doc(entity, id)
    if not doc:
        return False

    await db.delete(doc)
    if commit:
        await db.commit()

    return True


# =============================================================================
# apply_workflow_state
# =============================================================================

async def apply_workflow_state(
    entity: str,
    doc: Any,
    action_slug: str,
    db: AsyncSession,
    commit: bool = False,
) -> dict:
    """
    Validate a workflow transition and apply the new state to a document.

    This is the ONLY correct way to change workflow_state on a document.
    Never set workflow_state directly — always go through this function so
    that the transition is validated against the workflow configuration in
    the database.
    """
    import re
    from app.infrastructure.database.repositories.workflow_repository import WorkflowRepository

    workflow_repo = WorkflowRepository(db)
    current_state_raw = getattr(doc, "workflow_state", None) or ""
    current_state = current_state_raw.lower().strip()
    current_state = re.sub(r'[^a-z0-9\s_]', '', current_state)
    current_state = re.sub(r'\s+', '_', current_state)

    if not current_state:
        initial = await workflow_repo.get_initial_state(entity)
        if initial:
            current_state = initial
        else:
            return {"status": "error", "message": f"No workflow configured for '{entity}'"}

    is_valid, target_state, error = await workflow_repo.validate_transition(
        entity, current_state, action_slug, user=None
    )

    if not is_valid:
        return {
            "status": "error",
            "message": error or f"Action '{action_slug}' not valid from state '{current_state}'"
        }

    doc.workflow_state = target_state

    if commit:
        await db.flush()

    return {
        "status": "success",
        "from_state": current_state,
        "to_state": target_state,
    }
