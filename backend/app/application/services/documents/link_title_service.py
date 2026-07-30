"""
Link Title Service
==================
Resolves display names for link/foreign-key fields on entity records.

Extracted from the API layer to keep routers thin.
Consolidated from core/display_names.py to prevent duplication.
"""
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.meta.registry import MetaRegistry
from app.infrastructure.database.repositories.entity_repository import get_entity_model
from app.application.services.documents.document_query import get_doc


def _resolve_field_link(field) -> tuple[str | None, str | None, str | None]:
    """Return (field_name, field_type, link_entity) from a meta field object or dict."""
    if hasattr(field, "field_type"):
        field_type = field.field_type
        link_entity = getattr(field, "link_entity", None)
        child_entity = getattr(field, "child_entity", None)
        field_name = field.name
        query_key = getattr(getattr(field, "query", None), "key", None)
        if query_key is None and isinstance(getattr(field, "query", None), dict):
            query_key = (field.query or {}).get("key")
    elif isinstance(field, dict):
        field_type = field.get("field_type")
        link_entity = field.get("link_entity")
        child_entity = field.get("child_entity")
        field_name = field.get("name")
        query_key = (field.get("query") or {}).get("key")
    else:
        return None, None, None

    # Auto-resolve created_by and last_modified_by as user links
    if field_name in ("created_by", "last_modified_by"):
        return field_name, "link", "user"

    if field_type == "parent_child_link" and child_entity:
        link_entity = child_entity
        field_type = "link"

    if field_type == "query_link":
        if not link_entity and query_key:
            try:
                from app.application.services.documents.query_link import QUERY_LINK_TARGET_ENTITY
                link_entity = QUERY_LINK_TARGET_ENTITY.get(query_key)
            except Exception:
                link_entity = None
        field_type = "link"

    if field_type != "link":
        return field_name, None, None

    return field_name, field_type, link_entity


def inject_link_name_fields(meta: Any, record_dict: dict, link_titles: dict[str, str]) -> None:
    """Inject ``{field}_name`` display values into a record dict using pre-built link titles."""
    if not meta or not getattr(meta, "fields", None):
        return

    for field in meta.fields:
        field_name, field_type, link_entity = _resolve_field_link(field)
        if field_type != "link" or not link_entity or not field_name:
            continue

        fk_value = record_dict.get(field_name)
        if not fk_value:
            continue

        name_field = f"{field_name}_name"
        if record_dict.get(name_field) not in (None, ""):
            continue

        title = link_titles.get(f"{link_entity}::{fk_value}")
        if title:
            record_dict[name_field] = title


async def build_link_titles_batch(
    db: AsyncSession, meta: Any, records: list[dict]
) -> list[dict[str, str]]:
    """Build ``_link_titles`` dict for multiple records using batch queries."""
    if not meta.fields or not records:
        return [{} for _ in records]

    entity_fk_map: dict[str, set[str]] = {}
    field_entity_map: dict[str, str] = {}

    for field in meta.fields:
        field_name, field_type, link_entity = _resolve_field_link(field)
        if field_type != "link" or not link_entity or not field_name:
            continue

        field_entity_map[field_name] = link_entity

        fk_values = {str(r[field_name]) for r in records if r.get(field_name)}
        if fk_values:
            entity_fk_map[link_entity] = entity_fk_map.get(link_entity, set()) | fk_values

    linked_entities_data: dict[str, dict[str, str]] = {}
    for entity_name, fk_values in entity_fk_map.items():
        linked_meta = MetaRegistry.get(entity_name)
        linked_model = get_entity_model(entity_name)
        if not linked_meta or not linked_model:
            continue

        title_field = linked_meta.title_field or "id"
        try:
            result = await db.execute(
                select(linked_model).where(linked_model.id.in_(list(fk_values)))
            )
            entity_titles = {}
            for rec in result.scalars().all():
                rec_id = str(getattr(rec, "id", None))
                entity_titles[rec_id] = str(getattr(rec, title_field, None) or rec_id)
            linked_entities_data[entity_name] = entity_titles
        except Exception:
            continue

    records_link_titles = []
    for record in records:
        link_titles: dict[str, str] = {}
        for field_name, entity_name in field_entity_map.items():
            fk_value = record.get(field_name)
            if not fk_value:
                continue
            title = linked_entities_data.get(entity_name, {}).get(str(fk_value))
            if title:
                link_titles[f"{entity_name}::{fk_value}"] = title
        records_link_titles.append(link_titles)

    return records_link_titles


async def build_link_titles_single(
    db: AsyncSession, meta: Any, record: Any
) -> dict[str, str]:
    """Build ``_link_titles`` dict for a single record."""
    link_titles: dict[str, str] = {}

    # Always resolve ownership fields regardless of whether they appear in meta.fields,
    # because BaseModel adds them as system columns outside the entity metadata definition.
    OWNERSHIP_FIELDS = {"created_by": "user", "last_modified_by": "user"}
    field_entity_pairs: list[tuple[str, str]] = []

    if meta.fields:
        for field in meta.fields:
            field_name, field_type, link_entity = _resolve_field_link(field)
            if field_type == "link" and link_entity and field_name:
                field_entity_pairs.append((field_name, link_entity))

    for ownership_field, entity_name in OWNERSHIP_FIELDS.items():
        if not any(f == ownership_field for f, _ in field_entity_pairs):
            field_entity_pairs.append((ownership_field, entity_name))

    for field_name, link_entity in field_entity_pairs:
        fk_value = record.get(field_name) if isinstance(record, dict) else getattr(record, field_name, None)
        if not fk_value:
            continue

        linked_meta = MetaRegistry.get(link_entity)
        linked_model = get_entity_model(link_entity)
        if not linked_meta or not linked_model:
            continue

        title_field = linked_meta.title_field or "id"
        try:
            result = await db.execute(
                select(linked_model).where(linked_model.id == fk_value)
            )
            linked_record = result.scalar_one_or_none()
            if linked_record:
                title = str(getattr(linked_record, title_field, None) or fk_value)
                link_titles[f"{link_entity}::{fk_value}"] = title
        except Exception:
            pass

    return link_titles


async def get_link_title(
    entity_name: str,
    record_id: str | None,
    db: AsyncSession,
) -> str:
    """Get display title for a single entity record."""
    if not record_id:
        return ""

    meta = MetaRegistry.get(entity_name)
    title_field = meta.title_field if meta else "id"

    doc = await get_doc(entity_name, str(record_id), db, as_dict=True)
    if not doc:
        return str(record_id)

    value = doc.get(title_field)
    if value in (None, ""):
        return str(record_id)

    return str(value)


async def get_record_display_name(
    entity_name: str,
    record: Any,
    db: AsyncSession | None = None,
) -> str:
    """Get display name for a record (title field or ID)."""
    if record is None:
        return ""

    meta = MetaRegistry.get(entity_name)
    title_field = meta.title_field if meta else "id"

    if isinstance(record, dict):
        title_value = record.get(title_field)
        if title_value not in (None, ""):
            return str(title_value)
        record_id = record.get("id")
        if db and record_id and title_field != "id":
            return await get_link_title(entity_name, str(record_id), db)
        return str(record_id or "")

    title_value = getattr(record, title_field, None)
    if title_value not in (None, ""):
        return str(title_value)

    record_id = getattr(record, "id", None)
    if db and record_id and title_field != "id":
        return await get_link_title(entity_name, str(record_id), db)

    return str(record_id or "")


async def build_link_titles_for_record(
    meta: Any,
    record: Any,
    db: AsyncSession,
) -> dict[str, str]:
    """Legacy function - use build_link_titles_single() instead."""
    return await build_link_titles_single(db, meta, record)
