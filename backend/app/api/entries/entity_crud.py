"""
Entity CRUD Routes
===================
Create, Update, Delete operations for entities.
Thin handlers that delegate to EntityService.
"""
from typing import Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user_from_token, CurrentUser
from app.core.serialization import record_to_dict
from app.core.exceptions import ForbiddenError
from app.meta.registry import MetaRegistry
from app.schemas.base import ActionRequest, ActionResponse
from app.application.services.access_control.rbac_service import RBACAppService
from app.api.dependencies import get_db, get_current_user_from_token, get_rbac_service, get_workflow_service, get_naming_service
from app.api.entries.validation_helpers import (
    _humanize_pydantic_error,
    _humanize_field_name,
    _build_validation_message,
)
from app.application.services.workflows.workflow_service import WorkflowAppService
from app.application.services.documents.link_title_service import get_record_display_name
from app.application.hooks.registry import hook_registry
from app.application.hooks.context import SaveContext
from app.application.services.documents.server_actions import server_actions, ActionContext
from app.application.services.notifications.socketio import socket_manager
from app.application.services.documents.naming_service import NamingAppService
from app.application.services.documents.document_service import DocumentAppService
from app.application.services.base_entity_api import BaseEntityAPI, Context
from app.infrastructure.database.repositories.entity_repository import (
    EntityRepository,
    get_entity_model,
)
from app.core.sanitization import sanitize_dict
from app.api.entries.entity_children import BulkChildRequest, bulk_save_child_records, bulk_save_children


class BulkDeleteRequest(BaseModel):
    ids: list[str]


router = APIRouter(tags=["entity"])

ENTITY_APIS: dict[str, BaseEntityAPI] = {}


def get_entity_api(entity: str) -> BaseEntityAPI:
    return ENTITY_APIS.get(entity, BaseEntityAPI())


def get_entity_repository(db: AsyncSession) -> EntityRepository:
    return EntityRepository(db)


def _get_actor_id(user: CurrentUser) -> str | None:
    return None if user.id == "anonymous" else user.id


def _coerce_incoming_types(model: Any, data: dict[str, Any]) -> dict[str, Any]:
    from app.application.services.entity_service import EntityService
    return EntityService.coerce_incoming_types(model, data)


def _validate_schema(entity: str, meta: Any, data: dict[str, Any], action: str = "create") -> dict[str, str]:
    """
    Validate *data* against the generated Pydantic write schema for *entity*.

    Falls back to a manual required-field scan when no schema is registered
    (e.g. core system entities that skip schema generation).

    Returns a dict of {field_name: error_message} — empty means no errors.
    """
    from pydantic import ValidationError as PydanticValidationError

    write_schema = MetaRegistry.get_write_schema(entity)
    if write_schema is not None:
        # On update we only validate fields that are present in the write schema
        payload = data if action == "create" else {k: v for k, v in data.items() if k in write_schema.model_fields}
        try:
            write_schema.model_validate(payload)
            return {}
        except PydanticValidationError as exc:
            errors: dict[str, str] = {}
            for err in exc.errors():
                loc = err.get("loc", ())
                field_name = loc[0] if loc else "unknown"
                # Humanise the field name using meta when possible
                field_meta = next((f for f in (meta.fields or []) if f.name == field_name), None)
                label = _humanize_field_name(field_name, meta)
                is_required = bool(field_meta and field_meta.required)
                errors[str(field_name)] = _humanize_pydantic_error(err, label, is_required)
            return errors

    # ── Fallback: manual required check ─────────────────────────────────────
    errors = {}
    skip_fields = {"id", "created_at", "updated_at", "created_by", "last_modified_by", "workflow_state", "row_no"}
    for f in (meta.fields or []):
        if f.name in skip_fields:
            continue
        if not f.required:
            continue
        if action == "update" and f.name not in data:
            continue
        value = data.get(f.name)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            errors[f.name] = f"{f.label} is required"
    return errors


@router.post("/{entity}/action", name="post_entity_action")
async def post_entity_action(
    entity: str,
    request: ActionRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
    workflow_service: WorkflowAppService = Depends(get_workflow_service),
    naming_service: NamingAppService = Depends(get_naming_service),
):
    """Single CRUD endpoint for entity actions."""
    try:
        meta = MetaRegistry.get(entity)
        if not meta:
            return ActionResponse(status="error", message=f"Entity '{entity}' not found")

        user = await get_current_user_from_token(authorization, db)
        api = get_entity_api(entity)
        model = get_entity_model(entity)

        if not model:
            return ActionResponse(status="error", message=f"Model for '{entity}' not found")

        ctx = Context(db=db, user=user, meta=meta)

        entity_label = meta.label or entity.replace("_", " ").title()

        if request.action == "create":
            if not await rbac.check_permission(
                user_id=user.id,
                entity=entity,
                action="create",
                role_ids=user.role_ids,
                is_superuser=user.is_superuser
            ):
                raise ForbiddenError(f"You don't have permission to create {meta.label}")

            raw_data = sanitize_dict(request.data or {})

            # Validate payload via generated Pydantic schema (falls back to manual check)
            req_errors = _validate_schema(entity, meta, raw_data, "create")
            if req_errors:
                return ActionResponse(
                    status="error",
                    message=_build_validation_message(req_errors, meta),
                    errors=req_errors,
                )

            errors = await api.validate_create(raw_data, ctx)
            if errors:
                return ActionResponse(
                    status="error",
                    message=_build_validation_message(errors, meta),
                    errors=errors,
                )

            data = await api.before_create(raw_data, ctx)

            save_ctx = SaveContext(db=db, user=user, entity=entity, action="create", meta=meta)
            # Execute before_save hooks via registry
            hook_result = await hook_registry.execute_before_save(entity, data, save_ctx)
            if hook_result and isinstance(hook_result, dict) and "errors" in hook_result:
                return ActionResponse(
                    status="error",
                    message=_build_validation_message(hook_result["errors"], meta),
                    errors=hook_result["errors"],
                )
            elif hook_result and isinstance(hook_result, dict) and "data" in hook_result:
                data = hook_result["data"]

            if meta.naming and meta.naming.enabled:
                if not data.get("id"):
                    generated_id = await naming_service.generate_id(meta.naming, entity)
                    if generated_id:
                        data["id"] = generated_id

            # Auto-fill workflow_state from entity metadata when not provided
            if (
                meta.workflow and meta.workflow.enabled
                and data.get("workflow_state") in (None, "")
                and meta.workflow.initial_state
            ):
                data["workflow_state"] = meta.workflow.initial_state

            # If workflow is disabled in JSON but the table enforces NOT NULL on workflow_state,
            # fall back to DB workflow initial state when available.
            if data.get("workflow_state") in (None, "") and hasattr(model, "workflow_state"):
                try:
                    initial_state = await workflow_service.get_initial_state(entity)
                    if initial_state:
                        data["workflow_state"] = initial_state
                except Exception:
                    pass

            actor_id = _get_actor_id(user)
            if hasattr(model, "created_by"):
                data["created_by"] = actor_id
            if hasattr(model, "last_modified_by"):
                data["last_modified_by"] = actor_id

            data = _coerce_incoming_types(model, data)

            record = model(**data)
            db.add(record)

            try:
                await db.commit()
                await db.refresh(record)
            except Exception as e:
                await db.rollback()
                from sqlalchemy.exc import IntegrityError

                if isinstance(e, IntegrityError):
                    return ActionResponse(
                        status="error",
                        message="Database integrity error",
                        errors={"type": type(e).__name__, "error": str(e)},
                    )
                raise

            await api.after_create(record, ctx)
            # Execute after_save hooks via registry
            hook_result = await hook_registry.execute_after_save(entity, record, save_ctx)

            record_dict = record_to_dict(record)

            # Save children atomically if provided
            if request.children:
                parent_id = record_dict.get("id")
                if parent_id:
                    for child_entity, child_data in request.children.items():
                        bulk_req = BulkChildRequest(
                            rows=child_data.get("rows", []),
                            deleted_ids=child_data.get("deleted_ids", [])
                        )
                        # Use the same transaction for atomicity
                        child_result = await bulk_save_children(
                            entity, parent_id, child_entity, bulk_req, authorization, db,
                            rbac, workflow_service, naming_service
                        )
                        if child_result.status != "success":
                            await db.rollback()
                            return child_result

            await socket_manager.emit_created(entity, record_dict)
            await socket_manager.emit_post_save(entity, record_dict, "create", hook_result)

            created_label = await get_record_display_name(entity, record_dict, db)
            return ActionResponse(
                status="success",
                message=f"{entity_label} {created_label or (record_dict.get('id') or request.id or 'unknown')} created",
                data=record_dict,
            )

        elif request.action == "update":
            if not await rbac.check_permission(
                user_id=user.id,
                entity=entity,
                action="update",
                role_ids=user.role_ids,
                is_superuser=user.is_superuser
            ):
                raise ForbiddenError(f"You don't have permission to update {meta.label}")

            if not request.id:
                return ActionResponse(status="error", message="ID required for update")

            repo = EntityRepository(db)
            record = await repo.get_by_id(entity, request.id)

            if not record:
                return ActionResponse(status="error", message="Record not found")

            raw_data = sanitize_dict(request.data or {})

            # Validate payload via generated Pydantic schema (falls back to manual check)
            req_errors = _validate_schema(entity, meta, raw_data, "update")
            if req_errors:
                return ActionResponse(
                    status="error",
                    message=_build_validation_message(req_errors, meta),
                    errors=req_errors,
                )

            errors = await api.validate_update(request.id, raw_data, ctx)
            if errors:
                return ActionResponse(
                    status="error",
                    message=_build_validation_message(errors, meta),
                    errors=errors,
                )

            data = await api.before_update(record, raw_data, ctx)

            save_ctx = SaveContext(db=db, user=user, entity=entity, action="update", meta=meta)
            # Execute before_save hooks via registry
            hook_result = await hook_registry.execute_before_save(entity, data, save_ctx)
            if hook_result and isinstance(hook_result, dict) and "errors" in hook_result:
                return ActionResponse(
                    status="error",
                    message=_build_validation_message(hook_result["errors"], meta),
                    errors=hook_result["errors"],
                )
            elif hook_result and isinstance(hook_result, dict) and "data" in hook_result:
                data = hook_result["data"]

            data = _coerce_incoming_types(model, data)

            system_fields = {"id", "created_at", "updated_at", "created_by"}
            for key, value in data.items():
                if key in system_fields:
                    continue
                if hasattr(record, key):
                    setattr(record, key, value)

            if hasattr(record, "last_modified_by"):
                record.last_modified_by = _get_actor_id(user)

            try:
                await db.commit()
                await db.refresh(record)
            except Exception as e:
                await db.rollback()
                from sqlalchemy.exc import IntegrityError

                if isinstance(e, IntegrityError):
                    return ActionResponse(
                        status="error",
                        message="Database integrity error",
                        details={"type": type(e).__name__, "error": str(e)},
                    )
                raise

            await api.after_update(record, ctx)
            # Execute after_save hooks via registry
            hook_result = await hook_registry.execute_after_save(entity, record, save_ctx)
            await db.commit()

            # Save children atomically if provided
            if request.children:
                for child_entity, child_data in request.children.items():
                    bulk_req = BulkChildRequest(
                        rows=child_data.get("rows", []),
                        deleted_ids=child_data.get("deleted_ids", [])
                    )
                    # Use the same transaction for atomicity
                    child_result = await bulk_save_children(
                        entity, request.id, child_entity, bulk_req, authorization, db,
                        rbac, workflow_service, naming_service
                    )
                    if child_result.status != "success":
                        await db.rollback()
                        return child_result

            record_dict = record_to_dict(record)
            await socket_manager.emit_updated(entity, record_dict)
            await socket_manager.emit_post_save(entity, record_dict, "update", hook_result)

            updated_label = await get_record_display_name(entity, record_dict, db)
            return ActionResponse(
                status="success",
                message=f"{entity_label} {updated_label or (record_dict.get('id') or request.id or 'unknown')} updated",
                data=record_dict,
            )

        elif request.action == "delete":
            if not await rbac.check_permission(
                user_id=user.id,
                entity=entity,
                action="delete",
                role_ids=user.role_ids,
                is_superuser=user.is_superuser
            ):
                raise ForbiddenError(f"You don't have permission to delete {meta.label}")

            if not request.id:
                return ActionResponse(status="error", message="ID required for delete")

            repo = EntityRepository(db)
            record = await repo.get_by_id(entity, request.id)

            if not record:
                return ActionResponse(status="error", message="Record not found")

            await api.before_delete(record, ctx)

            record_id = record.id
            try:
                await db.delete(record)
                await db.commit()
            except Exception as e:
                await db.rollback()
                from sqlalchemy.exc import IntegrityError

                if isinstance(e, IntegrityError):
                    error_msg = str(e)
                    # Check if it's a foreign key violation
                    if "foreign key constraint" in error_msg.lower() or "ForeignKeyViolationError" in error_msg:
                        # Find all records that reference this entity
                        referencing_records = await repo.find_referencing_records(entity, record_id)

                        # Build a detailed error message with referencing records
                        if referencing_records:
                            ref_summary = []
                            for ref in referencing_records[:10]:  # Limit to first 10 records
                                entity_display = ref.get('entity_display', ref['entity'])
                                ref_summary.append(f"{entity_display} ({ref['id']}): {ref['display_name']}")
                            if len(referencing_records) > 10:
                                ref_summary.append(f"... and {len(referencing_records) - 10} more")

                            message = f"Cannot delete {entity_label}. It is still referenced by {len(referencing_records)} record(s)."
                        else:
                            message = f"Cannot delete this {entity_label}. It is still referenced by other records. Please remove or update the related records first."

                        return ActionResponse(
                            status="error",
                            message=message,
                            data={"referencing_records": referencing_records},
                        )
                    # Other integrity errors
                    return ActionResponse(
                        status="error",
                        message="Database integrity error. The operation could not be completed.",
                    )
                raise

            await api.after_delete(ctx)
            await socket_manager.emit_deleted(entity, record_id)

            deleted_label = await get_record_display_name(entity, {"id": record_id}, db)
            return ActionResponse(
                status="success",
                message=f"{entity_label} {deleted_label or (record_id or request.id or 'unknown')} deleted",
            )

        else:
            action_ctx = ActionContext(
                db=db, user=user, entity_name=entity,
                record_id=request.id, params=request.data or {}
            )
            result = await server_actions.execute(entity, request.action, action_ctx)
            return ActionResponse(**result)

    except Exception as e:
        try:
            await db.rollback()
        except Exception:
            pass
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Error in post_entity_action for {entity}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return ActionResponse(
            status="error", message=str(e),
            details={"type": type(e).__name__, "entity": entity,
                     "action": getattr(request, 'action', 'unknown')}
        )


@router.delete("/{entity}/{id}", name="delete_entity")
async def delete_entity(
    entity: str,
    id: str,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Delete a single record by ID using REST DELETE method."""
    from app.core.exceptions import NotFoundError, ForbiddenError

    meta = MetaRegistry.get(entity)
    if not meta:
        raise NotFoundError("Entity", entity)

    user = await get_current_user_from_token(authorization, db)
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="delete",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise ForbiddenError(f"You don't have permission to delete {meta.label}")

    model = get_entity_model(entity)
    if not model:
        raise NotFoundError("Model", entity)

    api = get_entity_api(entity)
    ctx = Context(db=db, user=user, meta=meta)

    repo = EntityRepository(db)
    record = await repo.get_by_id(entity, id)

    if not record:
        raise NotFoundError(meta.label, id)

    try:
        await api.before_delete(record, ctx)
        record_id = record.id
        await db.delete(record)
        await db.commit()
        await api.after_delete(ctx)
        await socket_manager.emit_deleted(entity, record_id)
        return ActionResponse(status="success", message="Record deleted")
    except Exception as e:
        await db.rollback()
        from sqlalchemy.exc import IntegrityError

        if isinstance(e, IntegrityError):
            error_msg = str(e)
            if "foreign key constraint" in error_msg.lower():
                # Find all records that reference this entity
                referencing_records = await repo.find_referencing_records(entity, id)

                # Build a detailed error message with referencing records
                if referencing_records:
                    ref_summary = []
                    for ref in referencing_records[:10]:  # Limit to first 10 records
                        entity_display = ref.get('entity_display', ref['entity'])
                        ref_summary.append(f"{entity_display} ({ref['id']}): {ref['display_name']}")
                    if len(referencing_records) > 10:
                        ref_summary.append(f"... and {len(referencing_records) - 10} more")

                    message = f"Cannot delete {meta.label}. It is still referenced by {len(referencing_records)} record(s)."
                else:
                    message = f"Cannot delete {meta.label}. It is referenced by other records."

                return ActionResponse(
                    status="error",
                    message=message,
                    data={"referencing_records": referencing_records},
                    details={"type": "foreign_key_violation", "error": error_msg}
                )
        raise


@router.post("/{entity}/bulk-delete", name="bulk_delete_entity")
async def bulk_delete_entity(
    entity: str,
    request: BulkDeleteRequest,
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
    rbac: RBACAppService = Depends(get_rbac_service),
):
    """Delete multiple records by IDs in a single transaction."""
    from app.core.exceptions import NotFoundError, ForbiddenError

    meta = MetaRegistry.get(entity)
    if not meta:
        raise NotFoundError("Entity", entity)

    user = await get_current_user_from_token(authorization, db)
    if not await rbac.check_permission(
        user_id=user.id,
        entity=entity,
        action="delete",
        role_ids=user.role_ids,
        is_superuser=user.is_superuser
    ):
        raise ForbiddenError(f"You don't have permission to delete {meta.label}")

    model = get_entity_model(entity)
    if not model:
        raise NotFoundError("Model", entity)

    api = get_entity_api(entity)
    ctx = Context(db=db, user=user, meta=meta)
    repo = EntityRepository(db)

    # Call before_delete hook for each record
    for record_id in request.ids:
        record = await repo.get_by_id(entity, record_id)
        if record:
            await api.before_delete(record, ctx)

    # Perform bulk delete
    deleted_count, failed_deletions, error_summary = await repo.bulk_delete(entity, request.ids)

    # Commit the outer transaction after all savepoint commits
    await db.commit()

    # Call after_delete hook once after all deletions
    await api.after_delete(ctx)

    # Emit socket events for deleted records
    for record_id in request.ids:
        # Only emit for successfully deleted records (not in failed list)
        if not any(f['id'] == record_id for f in failed_deletions):
            await socket_manager.emit_deleted(entity, record_id)

    # Build response
    if failed_deletions:
        # Partial or complete failure - return error status so frontend shows toast
        entity_label = meta.label or entity.replace("_", " ").title()
        if deleted_count == 0:
            message = f"Could not delete {len(request.ids)} {entity_label} record(s)."
        else:
            message = f"Deleted {deleted_count} of {len(request.ids)} {entity_label} record(s)."

        # Build summarized error message
        if error_summary:
            error_lines = []
            for error_type, count in error_summary.items():
                if error_type == "Foreign key constraint violation":
                    error_lines.append(f"{count} {entity_label} record(s) still referenced by other records.")
                elif error_type == "Record not found":
                    error_lines.append(f"{count} record(s) not found.")
                elif error_type == "Model not found":
                    error_lines.append(f"Model for {entity} not found.")
                else:
                    error_lines.append(f"{count} record(s) had {error_type.lower()}.")
            message += " Errors: " + " ".join(error_lines)

        return ActionResponse(
            status="error",
            message=message,
            data={
                "deleted_count": deleted_count,
                "failed_count": len(failed_deletions),
                "failed_deletions": failed_deletions,
                "error_summary": error_summary,
            },
        )
    else:
        # Full success
        entity_label = meta.label or entity.replace("_", " ").title()
        return ActionResponse(
            status="success",
            message=f"Successfully deleted {deleted_count} {entity_label} record(s)",
            data={"deleted_count": deleted_count},
        )


    # document_action route moved to entity_actions.py (SRP)
