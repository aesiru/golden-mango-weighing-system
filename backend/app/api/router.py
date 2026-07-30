"""
Master API Router - Consolidated API Layer
========================================
Central hub connecting all routes in the consolidated API structure.

Route groups:
  ENTRY   (/api/entity/*)    — generic entity CRUD kernel
  SYSTEM  (/api/*)           — infrastructure: auth, meta, workflow, import-export, admin,
                               profile, setup, health, version, attachments, feature-flags,
                               audit-log
  SERVICE (/api/*)           — shared utilities: notifications, email
  FEATURE (/api/features/*)  — product features: diagram, search, comments,
                               favorites, tags, timeline, notifications
  APP     (/api/*)           — cross-domain features: branding
  TEST    (/api/test/*)      — dev-only scheduler triggers
"""
from importlib import import_module
from collections.abc import Sequence
from enum import Enum
from typing import cast

from fastapi import APIRouter

# Create master router
api_router = APIRouter()


def _include_route_modules(
    module_paths: Sequence[str], *, prefix: str | None = None, tags: Sequence[str | Enum]
) -> None:
    for module_path in module_paths:
        router = import_module(module_path).router
        api_router.include_router(router, prefix=prefix or "", tags=cast(list[str | Enum], list(tags)))


# Generic entity CRUD kernel — all routes served under /api/entity/
ENTRY_ROUTE_MODULES = [
    "app.api.entries.entity_crud",
    "app.api.entries.entity_list",
    "app.api.entries.entity_workflow",
    "app.api.entries.entity_actions",
    "app.api.entries.entity_audit",
    "app.api.entries.entity_print",
    "app.api.entries.entity_options",
    "app.api.entries.entity_prefill",
    "app.api.entries.entity_children",
    "app.api.entries.entity_attachments",
    "app.api.entries.entity_tree",
    "app.api.entries.entity_fetch_from",
]

# Infrastructure concerns — routes served at their own prefixes under /api/
SYSTEM_ROUTE_MODULES = [
    "app.api.system.meta",
    "app.api.system.auth",
    "app.api.system.workflow",
    "app.api.system.import_export",
    "app.api.system.admin",
    "app.api.system.profile",
    "app.api.system.setup",
    "app.api.system.users",
    # New system endpoints
    "app.api.system.health",
    "app.api.system.version",
    "app.api.system.attachments",
    "app.api.system.feature_flags",
    "app.api.system.audit_log",
]

# Shared service utilities — kept for backward compat (shims to features/)
SERVICE_ROUTE_MODULES = [
    "app.api.services.notifications",
    "app.api.services.email",
]

# Platform-level app routes — cross-domain, no /features prefix
APP_ROUTE_MODULES = [
    "app.api.system.branding_settings",
]

# Product features — routes served under /api/features/
FEATURE_ROUTE_MODULES = [
    "app.api.features.warehouse_auth",
    "app.api.features.diagram",
    # New feature modules
    "app.api.features.search",
    "app.api.features.comments",
    "app.api.features.favorites",
    "app.api.features.tags",
    "app.api.features.timeline",
    "app.api.features.user_activity",
    # notifications served at /api/notifications via SERVICE_ROUTE_MODULES for backward compat
]

_include_route_modules(ENTRY_ROUTE_MODULES, prefix="/entity", tags=["Entities"])
_include_route_modules(SYSTEM_ROUTE_MODULES, tags=["System"])
# SERVICE modules are NOW shims; they re-export from features/ — included without prefix
# to preserve existing /api/notifications/... URLs
_include_route_modules(SERVICE_ROUTE_MODULES, tags=["Services"])
_include_route_modules(APP_ROUTE_MODULES, tags=["App"])
_include_route_modules(FEATURE_ROUTE_MODULES, prefix="/features", tags=["Features"])

# ---------------------------------------------------------------------------
# Module labels used by the custom OpenAPI post-processor in main.py
# ---------------------------------------------------------------------------

MODULE_LABELS: dict[str, dict[str, str]] = {
    "core": {
        "label": "Core Framework",
        "description": "Users, roles, permissions, workflows, audit logs, and system configuration.",
    },
}

__all__ = ["api_router", "MODULE_LABELS"]
