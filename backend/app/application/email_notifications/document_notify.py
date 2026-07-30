"""
Fire catalog emails after document insert (new_doc/save_doc path).
Entity CRUD uses SQLAlchemy directly; this covers the document service path.
"""
import logging
import re
from typing import Any

from app.application.email_notifications.catalog import (
    CATALOG_ID_CREATED,
    catalog_id_for_routing,
    get_catalog_entry,
)
from app.infrastructure.email.notification_factory import build_email_notification_dispatcher
from app.core.config import settings
from app.core.serialization import record_to_dict
from app.meta.registry import MetaRegistry

logger = logging.getLogger(__name__)


def _entity_table_name(doc: Any) -> str | None:
    table = getattr(doc.__class__, "__table__", None)
    return table.name if table is not None else None


def _action_url(entity: str, record_id: str | None) -> str | None:
    base = (settings.PUBLIC_APP_URL or "").rstrip("/")
    if not base or not record_id:
        return None
    return f"{base}/{entity}/{record_id}"


async def notify_after_document_insert(db, doc: Any) -> None:
    """If this row is a catalog-backed entity on first insert, send the \"created\" notification."""
    entity = _entity_table_name(doc)
    if not entity or entity not in CATALOG_ID_CREATED:
        return

    catalog_id = CATALOG_ID_CREATED[entity]
    if not get_catalog_entry(catalog_id):
        return

    try:
        d = record_to_dict(doc)
        dispatch = build_email_notification_dispatcher(db)
        url = _action_url(entity, d.get("id"))
        await dispatch.notify(catalog_id, d, action_url=url)
    except Exception:
        logger.warning(
            "document insert email notification failed entity=%s", entity, exc_info=True
        )


async def notify_after_workflow_transition(
    db,
    entity: str,
    doc_dict: dict,
    to_state_slug: str,
) -> None:
    """Email subscribers when a record enters a workflow state (slug from WorkflowDBService)."""
    if not to_state_slug:
        return
    slug = to_state_slug.lower().strip()
    slug = re.sub(r"[^a-z0-9\s_]", "", slug)
    slug = re.sub(r"\s+", "_", slug)
    slug = slug.strip("_")
    if not slug:
        return
    event = f"workflow_state:{slug}"
    cid = catalog_id_for_routing(entity, event)
    if not cid:
        return
    try:
        dispatch = build_email_notification_dispatcher(db)
        url = _action_url(entity, doc_dict.get("id"))
        await dispatch.notify(cid, doc_dict, action_url=url)
    except Exception:
        logger.warning(
            "workflow transition email failed entity=%s event=%s",
            entity,
            event,
            exc_info=True,
        )
