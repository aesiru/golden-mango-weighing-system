"""
Developer-maintained list of email notifications users may subscribe to.

Includes:
- \"created\" for key entities (also fired from document insert path)
- workflow_state:<slug> for each workflow target state (fired on transition)
- inventory / scheduler-specific events
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class NotificationCatalogEntry:
    catalog_id: str
    title: str
    description: str
    entity_type: str
    event: str
    category: str = "General"


def _wf(
    entity: str,
    entity_label: str,
    category: str,
    slug: str,
    state_label: str,
) -> NotificationCatalogEntry:
    return NotificationCatalogEntry(
        catalog_id=f"email.{entity}.workflow.{slug}",
        title=f"{entity_label}: {state_label}",
        description=(
            f"Email when a {entity_label.lower()} moves to workflow state “{state_label}”."
        ),
        entity_type=entity,
        event=f"workflow_state:{slug}",
        category=category,
    )


# purchase_request workflow slugs (see entity metadata + tests)
# Note: 'draft' excluded as it's the initial state - covered by 'created' event
_PR_STATES: tuple[tuple[str, str], ...] = (
    ("pending_review", "Pending Review"),
    ("pending_approval", "Pending Approval"),
    ("approved", "Approved"),
    ("closed", "Closed"),
    ("rejected", "Rejected"),
)

# work_order workflow slugs
# Note: 'requested' excluded as it's the initial state - covered by 'created' event
_WO_STATES: tuple[tuple[str, str], ...] = (
    ("approved", "Approved"),
    ("in_progress", "In Progress"),
    ("closed", "Closed"),
)

# maintenance_request workflow slugs
# Note: 'draft' excluded as it's the initial state - covered by 'created' event
_MR_STATES: tuple[tuple[str, str], ...] = (
    ("pending_approval", "Pending Approval"),
    ("approved", "Approved"),
    ("release", "Release"),
    ("completed", "Completed"),
)


def _build_catalog() -> tuple[NotificationCatalogEntry, ...]:
    """Build the list of configured email notification catalog entries."""
    return tuple()


_CATALOG: tuple[NotificationCatalogEntry, ...] = _build_catalog()
_BY_ID: dict[str, NotificationCatalogEntry] = {e.catalog_id: e for e in _CATALOG}

CATALOG_ID_CREATED: dict[str, str] = {}


def list_catalog_entries() -> list[NotificationCatalogEntry]:
    return list(_CATALOG)


def get_catalog_entry(catalog_id: str) -> Optional[NotificationCatalogEntry]:
    return _BY_ID.get(catalog_id)


def require_catalog_entry(catalog_id: str) -> NotificationCatalogEntry:
    entry = get_catalog_entry(catalog_id)
    if not entry:
        raise ValueError(f"Unknown notification catalog_id: {catalog_id}")
    return entry


def is_catalog_entity_event(entity_type: str, event: str) -> bool:
    return any(e.entity_type == entity_type and e.event == event for e in _CATALOG)


def catalog_id_for_routing(entity_type: str, event: str) -> Optional[str]:
    for e in _CATALOG:
        if e.entity_type == entity_type and e.event == event:
            return e.catalog_id
    return None
