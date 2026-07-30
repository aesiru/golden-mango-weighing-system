"""
Entity Children Routes
=======================
Bulk CRUD operations for parent-child entity relationships.
Supports saving all child rows in a single atomic transaction.
"""
from typing import Any, Optional, List
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_db, get_current_user_from_token
from app.core.security import CurrentUser
from app.api.entries.validation_helpers import extract_field_label_from_error
from app.core.serialization import record_to_dict
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.sanitization import sanitize_dict
from app.meta.registry import MetaRegistry
from app.schemas.base import ActionResponse
from app.application.services.access_control.rbac_service import RBACAppService
from app.api.dependencies import get_rbac_service, get_workflow_service, get_naming_service, get_document_service
from app.application.services.workflows.workflow_service import WorkflowAppService
from app.application.services.documents.naming_service import NamingAppService
from app.application.services.documents.document_service import DocumentAppService
from app.infrastructure.database.repositories.entity_repository import get_entity_model
from app.application.hooks.context import SaveContext
from app.application.hooks.registry import hook_registry
from app.application.services.notifications.socketio import socket_manager

router = APIRouter(tags=["entity-children"])


class BulkChildRequest(BaseModel):
    """Request body for bulk child save."""
    rows: List[dict[str, Any]]
    deleted_ids: Optional[List[str]] = None


def _coerce_incoming_types(model: Any, data: dict[str, Any]) -> dict[str, Any]:
    from app.application.services.entity_service import EntityService
    return EntityService.coerce_incoming_types(model, data)


def _get_actor_id(user: CurrentUser) -> str | None:
    return None if user.id == "anonymous" else user.id


@router.get("/{entity}/{record_id}/children/{child_entity}", name="get_child_records")
async def get_child_records(
    entity: str,
    record_id: str,
    child_entity: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    document_service: DocumentAppService = Depends(get_document_service),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Get all child records for a parent entity record."""
    parent_meta = MetaRegistry.get(entity)
    if not parent_meta:
        raise NotFoundError("Entity", entity)

    child_meta = MetaRegistry.get(child_entity)
    if not child_meta:
        raise NotFoundError("Entity", child_entity)

    user = await get_current_user_from_token(authorization, db)
    if not await rbac.check_permission(
        user_id=user.id,
        entity=child_entity,
        action="read",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise ForbiddenError(f"You don't have permission to read {child_meta.label}")

    # Find the FK field linking child to parent
    fk_field = _find_fk_field(parent_meta, child_entity)
    if not fk_field:
        return ActionResponse(
            status="error",
            message=f"No link found between {entity} and {child_entity}"
        )

    child_model = get_entity_model(child_entity)
    if not child_model:
        raise NotFoundError("Model", child_entity)

    # Query all child records
    stmt = select(child_model).where(getattr(child_model, fk_field) == record_id)
    result = await db.execute(stmt)
    records = result.scalars().all()

    rows = [record_to_dict(r) for r in records]

    # Build _link_titles for all rows (child link fields)
    link_titles: dict[str, str] = {}
    try:
      for r in rows:
        per_row = await document_service.build_link_titles_single(child_meta, r)
        link_titles.update(per_row)
    except Exception:
      # Never fail child list because of link title resolution
      pass

    return {
        "status": "success",
        "data": rows,
        "total": len(rows),
        "child_entity": child_entity,
        "fk_field": fk_field,
        "_link_titles": link_titles,
    }


@router.post("/{entity}/{record_id}/children/{child_entity}/bulk-save")
async def bulk_save_child_records(
    entity: str,
    record_id: str,
    child_entity: str,
    request: BulkChildRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    workflow_service: WorkflowAppService = Depends(get_workflow_service),
    naming_service: NamingAppService = Depends(get_naming_service),
):
    """
    Bulk save child records for a parent entity in a single atomic transaction.

    For each row in request.rows:
    - If row has an 'id' that exists in DB → update
    - If row has no 'id' or id is empty → create new
    For each id in request.deleted_ids:
    - Delete the record

    All operations happen in one transaction (atomic).
    """
    parent_meta = MetaRegistry.get(entity)
    if not parent_meta:
        raise NotFoundError("Entity", entity)

    child_meta = MetaRegistry.get(child_entity)
    if not child_meta:
        raise NotFoundError("Entity", child_entity)

    user = await get_current_user_from_token(authorization, db)

    # Check permissions
    has_create = await rbac.check_permission(
        user_id=user.id,
        entity=child_entity,
        action="create",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )
    has_update = await rbac.check_permission(
        user_id=user.id,
        entity=child_entity,
        action="update",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )
    has_delete = await rbac.check_permission(
        user_id=user.id,
        entity=child_entity,
        action="delete",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    )

    # Find FK field
    fk_field = _find_fk_field(parent_meta, child_entity)
    if not fk_field:
        return ActionResponse(
            status="error",
            message=f"No link found between {entity} and {child_entity}"
        )

    child_model = get_entity_model(child_entity)
    if not child_model:
        raise NotFoundError("Model", child_entity)

    # Verify parent exists
    parent_model = get_entity_model(entity)
    if parent_model:
        parent_result = await db.execute(
            select(parent_model).where(parent_model.id == record_id)
        )
        if not parent_result.scalar_one_or_none():
            return ActionResponse(status="error", message=f"Parent record {record_id} not found")

    try:
        created = []
        updated = []
        hook_results: dict[str, dict[str, Any]] = {}
        deleted_count = 0
        errors = []

        # 1. Process deletes first
        if request.deleted_ids:
            if not has_delete:
                raise ForbiddenError(f"You don't have permission to delete {child_meta.label}")

            for del_id in request.deleted_ids:
                result = await db.execute(
                    select(child_model).where(child_model.id == del_id)
                )
                record = result.scalar_one_or_none()
                if record:
                    await db.delete(record)
                    deleted_count += 1

        # 2. Process creates and updates
        for idx, row_data in enumerate(request.rows):
            raw_data = sanitize_dict(row_data)

            # Always set the FK to point to parent
            raw_data[fk_field] = record_id

            # Remove system fields that shouldn't be sent
            row_id = raw_data.pop("id", None) or raw_data.pop("_id", None)
            raw_data.pop("created_at", None)
            raw_data.pop("updated_at", None)
            raw_data.pop("created_by", None)
            raw_data.pop("last_modified_by", None)

            is_update = row_id and not str(row_id).startswith("__new__")

            # Schema-backed validation
            from pydantic import ValidationError as PydanticValidationError
            child_write_schema = MetaRegistry.get_write_schema(child_entity)
            if child_write_schema is not None:
                validation_payload = raw_data if not is_update else {
                    k: v for k, v in raw_data.items() if k in child_write_schema.model_fields
                }
                try:
                    child_write_schema.model_validate(validation_payload)
                except PydanticValidationError as ve:
                    from app.api.entries.entity_crud import _humanize_pydantic_error
                    row_errors: dict[str, str] = {}
                    for err in ve.errors():
                        loc = err.get("loc", ())
                        field_name = loc[0] if loc else "unknown"
                        field_meta_obj = next(
                            (f for f in (child_meta.fields or []) if f.name == field_name), None
                        )
                        label = field_meta_obj.label if field_meta_obj else str(field_name).replace("_", " ").title()
                        is_required = bool(field_meta_obj and field_meta_obj.required)
                        row_errors[str(field_name)] = _humanize_pydantic_error(err, label, is_required)
                    errors.append({"row": idx, "error": row_errors})
                    continue

            if is_update:
                # UPDATE existing record
                if not has_update:
                    errors.append({"row": idx, "error": "No update permission"})
                    continue

                result = await db.execute(
                    select(child_model).where(child_model.id == row_id)
                )
                record = result.scalar_one_or_none()

                if not record:
                    errors.append({"row": idx, "error": f"Record {row_id} not found"})
                    continue

                save_ctx = SaveContext(
                    db=db, user=user, entity=child_entity,
                    action="update", meta=child_meta
                )
                hook_result = await hook_registry.execute_before_save(
                    child_entity, raw_data, save_ctx
                )
                if hook_result and isinstance(hook_result, dict):
                    if "errors" in hook_result:
                        errors.append({"row": idx, "error": hook_result["errors"]})
                        continue
                    if "data" in hook_result:
                        raw_data = hook_result["data"]

                coerced = _coerce_incoming_types(child_model, raw_data)

                system_fields = {"id", "created_at", "updated_at", "created_by"}
                for key, value in coerced.items():
                    if key in system_fields:
                        continue
                    if hasattr(record, key):
                        setattr(record, key, value)

                if hasattr(record, "last_modified_by"):
                    record.last_modified_by = _get_actor_id(user)

                after_res = await hook_registry.execute_after_save(child_entity, record, save_ctx)
                if after_res is not None:
                    hook_results[str(row_id)] = {"action": "update", "result": after_res}
                updated.append(record)
            else:
                # CREATE new record
                if not has_create:
                    errors.append({"row": idx, "error": "No create permission"})
                    continue

                save_ctx = SaveContext(
                    db=db, user=user, entity=child_entity,
                    action="create", meta=child_meta
                )
                hook_result = await hook_registry.execute_before_save(
                    child_entity, raw_data, save_ctx
                )
                if hook_result and isinstance(hook_result, dict):
                    if "errors" in hook_result:
                        errors.append({"row": idx, "error": hook_result["errors"]})
                        continue
                    if "data" in hook_result:
                        raw_data = hook_result["data"]

                # Generate naming ID
                if child_meta.naming and child_meta.naming.enabled:
                    generated_id = await naming_service.generate_id(child_meta.naming, child_entity)
                    if generated_id:
                        raw_data["id"] = generated_id

                # Auto-fill workflow_state
                if (
                    child_meta.workflow and child_meta.workflow.enabled
                    and raw_data.get("workflow_state") in (None, "")
                    and child_meta.workflow.initial_state
                ):
                    raw_data["workflow_state"] = child_meta.workflow.initial_state

                if raw_data.get("workflow_state") in (None, "") and hasattr(child_model, "workflow_state"):
                    try:
                        initial_state = await workflow_service.get_initial_state(child_entity)
                        if initial_state:
                            raw_data["workflow_state"] = initial_state
                    except Exception:
                        pass

                actor_id = _get_actor_id(user)
                if hasattr(child_model, "created_by"):
                    raw_data["created_by"] = actor_id
                if hasattr(child_model, "last_modified_by"):
                    raw_data["last_modified_by"] = actor_id

                coerced = _coerce_incoming_types(child_model, raw_data)
                record = child_model(**coerced)
                db.add(record)

                after_res = await hook_registry.execute_after_save(child_entity, record, save_ctx)
                created.append(record)
                # record.id may not exist yet; store on refresh phase
                if after_res is not None:
                    hook_results[f"__created__:{len(created)-1}"] = {"action": "create", "result": after_res}

        if errors:
            await db.rollback()
            # Build user-friendly error message
            failed_rows = [e["row"] + 1 for e in errors]  # Convert to 1-based
            failed_fields = []
            for err in errors:
                if isinstance(err.get("error"), dict):
                    for field_name, error_msg in err["error"].items():
                        if isinstance(error_msg, str):
                            label = extract_field_label_from_error(error_msg, field_name)
                            failed_fields.append(label)
                        else:
                            failed_fields.append(field_name.replace("_", " ").title())
            
            message = f"Validation failed for Row {', '.join(map(str, failed_rows))}"
            if failed_fields:
                # Get unique field labels
                unique_fields = list(dict.fromkeys(failed_fields))  # Preserve order, remove duplicates
                message += f". {', '.join(unique_fields)} required"
            
            return ActionResponse(
                status="error",
                message=message,
                errors={"rows": str(errors)}  # Convert list to string for schema compatibility
            )

        # Commit all changes atomically
        await db.commit()

        # Refresh all records to get DB-generated values
        all_records = []
        created_ids = {id(r) for r in created}
        created_idx = 0
        for record in created + updated:
            await db.refresh(record)
            rec_dict = record_to_dict(record)
            all_records.append(rec_dict)

            # Emit standard entity + post_save events so the frontend can toast
            if id(record) in created_ids:
                await socket_manager.emit_created(child_entity, rec_dict)
                hr = hook_results.get(f"__created__:{created_idx}")
                created_idx += 1
                await socket_manager.emit_post_save(
                    child_entity,
                    rec_dict,
                    "create",
                    (hr.get("result") if hr else None),
                )
            else:
                await socket_manager.emit_updated(child_entity, rec_dict)
                hr = hook_results.get(str(rec_dict.get("id")))
                await socket_manager.emit_post_save(
                    child_entity,
                    rec_dict,
                    "update",
                    (hr.get("result") if hr else None),
                )

        return ActionResponse(
            status="success",
            message=f"Saved {len(created)} new, {len(updated)} updated, {deleted_count} deleted",
            data={
                "rows": all_records,
                "created": len(created),
                "updated": len(updated),
                "deleted": deleted_count,
            }
        )

    except ForbiddenError:
        raise
    except Exception as e:
        await db.rollback()
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Bulk child save error for {entity}/{child_entity}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return ActionResponse(
            status="error",
            message=str(e),
        )


async def bulk_save_children(
    entity: str,
    record_id: str,
    child_entity: str,
    bulk_req: BulkChildRequest,
    authorization: Optional[str],
    db: AsyncSession,
    rbac: "RBACAppService",
    workflow_service: "WorkflowAppService",
    naming_service: "NamingAppService",
) -> ActionResponse:
    """
    Helper function to call bulk_save_child_records without FastAPI dependencies.
    This is used internally by entity_crud.py for atomic child saves.

    Services are passed as parameters to follow CLEAN architecture dependency inversion.
    """
    return await bulk_save_child_records(
        entity=entity,
        record_id=record_id,
        child_entity=child_entity,
        request=bulk_req,
        authorization=authorization,
        db=db,
        rbac=rbac,
        workflow_service=workflow_service,
        naming_service=naming_service,
    )


def _find_fk_field(parent_meta, child_entity: str) -> Optional[str]:
    """Find the FK field that links child_entity to parent entity.

    Checks both 'children' (inline child tables) and 'links' (related tabs).
    Links are stored as dicts in the registry.
    """
    # Check inline children first
    for child in (parent_meta.children or []):
        entity = child.entity if hasattr(child, "entity") else child.get("entity")
        fk = child.fk_field if hasattr(child, "fk_field") else child.get("fk_field")
        if entity == child_entity and fk:
            return fk

    # Fall back to links (stored as dicts)
    for link in (parent_meta.links or []):
        entity = link.get("entity") if isinstance(link, dict) else getattr(link, "entity", None)
        fk = link.get("fk_field") if isinstance(link, dict) else getattr(link, "fk_field", None)
        if entity == child_entity and fk:
            return fk

    return None
