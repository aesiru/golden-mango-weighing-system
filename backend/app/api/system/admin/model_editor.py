"""
Model Editor Router
===================
Thin API layer for entity metadata editing.
All orchestration is handled by MetadataSyncService (application layer).

Architecture: Frappe-inspired atomic save.
  Save = validate → backup → save JSON → reload registry → update model → migrate DB
  All in one request. No manual steps. No desync possible.
"""
from fastapi import APIRouter, Depends, HTTPException, Body
from app.core.security import get_current_user_from_token, CurrentUser
from app.api.dependencies import get_metadata_sync_service
from app.application.services.integrations.metadata_sync_service import MetadataSyncService
from app.application.services.notifications.socketio import socket_manager
from .common import api_response

router = APIRouter(tags=["admin-model-editor"])


def _require_superuser(user: CurrentUser):
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required")


# ------------------------------------------------------------------
# Entity CRUD
# ------------------------------------------------------------------

@router.get("/model-editor/entities")
async def list_editable_entities(
    current_user: CurrentUser = Depends(get_current_user_from_token),
    sync: MetadataSyncService = Depends(get_metadata_sync_service),
):
    """List all entities available for editing."""
    _require_superuser(current_user)
    entities = sync.list_entities()
    return api_response(
        status="success",
        message=f"Found {len(entities)} entities",
        data=entities,
    )


@router.get("/model-editor/field-types")
async def get_field_types(
    current_user: CurrentUser = Depends(get_current_user_from_token),
):
    """Get available field types and their configurations."""
    _require_superuser(current_user)
    field_types = [
        {"value": "string", "label": "String", "description": "Short text (max 255 chars)"},
        {"value": "text", "label": "Text", "description": "Long text (unlimited)"},
        {"value": "int", "label": "Integer", "description": "Whole numbers"},
        {"value": "float", "label": "Float", "description": "Decimal numbers"},
        {"value": "boolean", "label": "Boolean", "description": "True/False"},
        {"value": "date", "label": "Date", "description": "Date only"},
        {"value": "datetime", "label": "DateTime", "description": "Date and time"},
        {"value": "link", "label": "Link", "description": "Reference to another entity"},
        {"value": "parent_child_link", "label": "Parent-Child Link", "description": "Grouped selection by parent"},
        {"value": "query_link", "label": "Query Link", "description": "Dynamic query-based options"},
        {"value": "select", "label": "Select", "description": "Dropdown selection"},
        {"value": "attach", "label": "Attachment", "description": "File attachment"},
    ]
    return api_response(status="success", message="Field types retrieved", data=field_types)


@router.get("/model-editor/entity/{entity_name}")
async def get_entity_for_editing(
    entity_name: str,
    current_user: CurrentUser = Depends(get_current_user_from_token),
    sync: MetadataSyncService = Depends(get_metadata_sync_service),
):
    """Get full entity metadata for editing."""
    _require_superuser(current_user)
    metadata = sync.get_entity(entity_name)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Entity '{entity_name}' not found")

    model_status = sync.get_model_status(metadata)
    return api_response(
        status="success",
        message=f"Entity '{entity_name}' metadata retrieved",
        data={
            "metadata": metadata,
            "model_status": {
                "exists": model_status.get("exists", False),
                "has_changes": model_status.get("has_changes", False),
            },
        },
    )


@router.put("/model-editor/entity/{entity_name}")
async def save_entity(
    entity_name: str,
    metadata: dict = Body(...),
    current_user: CurrentUser = Depends(get_current_user_from_token),
    sync: MetadataSyncService = Depends(get_metadata_sync_service),
):
    """
    Atomic save: validate → backup → save JSON → reload registry
    → update model → generate migration → apply migration.

    This is the single endpoint that replaces the old multi-step workflow.
    """
    _require_superuser(current_user)

    # Optional flag can be passed inside metadata payload.
    # Keep a single request body contract (top-level metadata dict)
    # to avoid FastAPI requiring a nested {"metadata": {...}} shape.
    body_auto_migrate = (
        metadata.pop("auto_migrate", True)
        if isinstance(metadata.get("auto_migrate"), bool)
        else True
    )

    result = sync.save_and_sync(
        entity_name,
        metadata,
        auto_migrate=body_auto_migrate,
    )

    # Emit real-time event so other clients refresh
    if result.success:
        await socket_manager.emit_meta_change(
            "model-editor:entity",
            {"entity": entity_name},
        )

    return api_response(
        status="success" if result.success else "error",
        message=result.message,
        data={
            "json_saved": result.json_saved,
            "registry_reloaded": result.registry_reloaded,
            "model_updated": result.model_updated,
            "migration_generated": result.migration_generated,
            "migration_applied": result.migration_applied,
            "backup_path": result.backup_path,
            "model_path": result.model_path,
            "migration_file": result.migration_file,
            "changes": {
                "is_safe": result.changes.is_safe if result.changes else True,
                "items": [
                    {
                        "field": c.field_name,
                        "type": c.change_type.value,
                        "description": c.description,
                    }
                    for c in (result.changes.changes if result.changes else [])
                ],
            },
            "warnings": result.warnings,
            "errors": result.errors,
        },
    )


# ------------------------------------------------------------------
# Preview (read-only)
# ------------------------------------------------------------------

@router.put("/model-editor/entity/{entity_name}/save-draft")
async def save_entity_draft(
    entity_name: str,
    metadata: dict = Body(...),
    current_user: CurrentUser = Depends(get_current_user_from_token),
    sync: MetadataSyncService = Depends(get_metadata_sync_service),
):
    """
    Draft save: validate → backup → save JSON → reload registry.
    Skips model file update and migration — those are deferred to
    a server restart or an explicit 'Sync All' call.

    This is the Frappe-like approach: edit the doctype, then `bench migrate`.
    """
    _require_superuser(current_user)

    result = sync.save_json_only(entity_name, metadata)

    if result.success:
        await socket_manager.emit_meta_change(
            "model-editor:entity",
            {"entity": entity_name},
        )

    return api_response(
        status="success" if result.success else "error",
        message=result.message,
        data={
            "json_saved": result.json_saved,
            "registry_reloaded": result.registry_reloaded,
            "model_updated": False,
            "migration_generated": False,
            "migration_applied": False,
            "backup_path": result.backup_path,
            "warnings": result.warnings,
            "errors": result.errors,
        },
    )


@router.post("/model-editor/sync-all")
async def sync_all_entities(
    current_user: CurrentUser = Depends(get_current_user_from_token),
    sync: MetadataSyncService = Depends(get_metadata_sync_service),
):
    """
    Sync all entity models and apply pending migrations.
    Like Frappe's `bench migrate` — scans all entity JSONs, updates
    model files where needed, then generates + applies a single migration.
    """
    _require_superuser(current_user)
    try:
        result = sync.sync_pending()
        return api_response(
            status="success" if result.get("success") else "error",
            message=result.get("message", ""),
            data=result,
        )
    except Exception as e:
        return api_response(
            status="error",
            message=f"Sync failed: {str(e)}",
        )


@router.post("/model-editor/entity/{entity_name}/preview-changes")
async def preview_entity_changes(
    entity_name: str,
    metadata: dict = Body(...),
    current_user: CurrentUser = Depends(get_current_user_from_token),
    sync: MetadataSyncService = Depends(get_metadata_sync_service),
):
    """Preview changes without saving."""
    _require_superuser(current_user)
    preview = sync.preview_changes(entity_name, metadata)
    if not preview.get("valid", True):
        return api_response(
            status="error",
            message="Validation failed",
            data={"errors": preview.get("errors", [])},
        )
    return api_response(status="success", message="Changes analyzed", data=preview)


# ------------------------------------------------------------------
# Migration management
# ------------------------------------------------------------------

@router.get("/model-editor/migration/status")
async def get_migration_status(
    current_user: CurrentUser = Depends(get_current_user_from_token),
    sync: MetadataSyncService = Depends(get_metadata_sync_service),
):
    """Get current migration status."""
    _require_superuser(current_user)
    data = sync.get_migration_status()
    return api_response(status="success", message="Migration status retrieved", data=data)


@router.post("/model-editor/migration/apply")
async def apply_migrations(
    revision: str = Body(default="head", embed=True),
    current_user: CurrentUser = Depends(get_current_user_from_token),
    sync: MetadataSyncService = Depends(get_metadata_sync_service),
):
    """Apply pending migrations."""
    _require_superuser(current_user)
    result = sync.apply_migrations(revision)
    return api_response(
        status="success" if result.get("success") else "error",
        message=result.get("message", result.get("error", "Unknown error")),
        data=result,
    )


@router.post("/model-editor/migration/rollback")
async def rollback_migrations(
    steps: int = Body(default=1, embed=True),
    current_user: CurrentUser = Depends(get_current_user_from_token),
    sync: MetadataSyncService = Depends(get_metadata_sync_service),
):
    """Rollback migrations by number of steps."""
    _require_superuser(current_user)
    result = sync.rollback_migrations(steps)
    return api_response(
        status="success" if result.get("success") else "error",
        message=result.get("message", result.get("error", "Unknown error")),
        data=result,
    )


# ------------------------------------------------------------------
# Backups
# ------------------------------------------------------------------

@router.get("/model-editor/entity/{entity_name}/backups")
async def list_entity_backups(
    entity_name: str,
    current_user: CurrentUser = Depends(get_current_user_from_token),
    sync: MetadataSyncService = Depends(get_metadata_sync_service),
):
    """List available backups for an entity."""
    _require_superuser(current_user)
    backups = sync.list_backups(entity_name)
    return api_response(
        status="success",
        message=f"Found {len(backups)} backups",
        data=backups,
    )


@router.post("/model-editor/entity/{entity_name}/restore")
async def restore_entity_backup(
    entity_name: str,
    backup_filename: str = Body(..., embed=True),
    current_user: CurrentUser = Depends(get_current_user_from_token),
    sync: MetadataSyncService = Depends(get_metadata_sync_service),
):
    """Restore entity metadata from a backup and re-sync everything."""
    _require_superuser(current_user)
    result = sync.restore_backup(entity_name, backup_filename)

    if result.success:
        await socket_manager.emit_meta_change(
            "model-editor:entity",
            {"entity": entity_name},
        )

    return api_response(
        status="success" if result.success else "error",
        message=result.message,
        data={
            "json_saved": result.json_saved,
            "registry_reloaded": result.registry_reloaded,
            "model_updated": result.model_updated,
            "migration_generated": result.migration_generated,
            "migration_applied": result.migration_applied,
            "warnings": result.warnings,
        },
    )


# ------------------------------------------------------------------
# Bulk / System operations
# ------------------------------------------------------------------

@router.post("/model-editor/reload-metadata")
async def reload_metadata_registry(
    current_user: CurrentUser = Depends(get_current_user_from_token),
    sync: MetadataSyncService = Depends(get_metadata_sync_service),
):
    """Reload all entity metadata into the registry."""
    _require_superuser(current_user)
    try:
        count = sync.reload_all_metadata()
        return api_response(
            status="success",
            message=f"Reloaded {count} entities",
            data={"entity_count": count},
        )
    except Exception as e:
        return api_response(
            status="error",
            message=f"Failed to reload metadata: {str(e)}",
        )
