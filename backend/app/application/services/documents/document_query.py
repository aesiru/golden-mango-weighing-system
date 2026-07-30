"""
Document Query Service
======================
Read-only document operations (SRP: queries only).

Provides:
- get_doc: Fetch a document by entity name and ID
- get_meta: Get entity metadata from MetaRegistry
- get_value: Get specific field value(s)
- get_list: Fetch multiple documents
"""
from typing import Any, Optional, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.meta.registry import MetaRegistry, EntityMeta
from app.core.database import Base
from app.infrastructure.database.query.filter_builder import build_filter_condition


# =============================================================================
# MODEL REGISTRY (cached lookups)
# =============================================================================

_MODEL_CACHE: dict[str, Any] = {}
_MODELS_LOADED = False


def _ensure_models_loaded() -> None:
    global _MODELS_LOADED
    if _MODELS_LOADED:
        return

    try:
        from app.core.loader import load_modules
        from app.infrastructure.database.repositories.entity_repository import register_core_models

        load_modules()
        register_core_models()
        _MODELS_LOADED = True
    except Exception:
        pass


def _get_model(entity: str) -> Optional[Any]:
    """Get SQLAlchemy model class by entity name."""
    if entity in _MODEL_CACHE:
        return _MODEL_CACHE[entity]

    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if hasattr(cls, "__tablename__") and cls.__tablename__ == entity:
            _MODEL_CACHE[entity] = cls
            return cls

    _ensure_models_loaded()

    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if hasattr(cls, "__tablename__") and cls.__tablename__ == entity:
            _MODEL_CACHE[entity] = cls
            return cls

    return None


def _record_to_dict(doc: Any) -> dict:
    """Convert SQLAlchemy model instance to dict."""
    from app.core.serialization import record_to_dict
    return record_to_dict(doc)


# =============================================================================
# get_meta
# =============================================================================

def get_meta(entity: str) -> Optional[EntityMeta]:
    """Get entity metadata by name."""
    meta = MetaRegistry.get(entity)
    if meta is not None:
        return meta

    try:
        from app.entities import load_all_entities

        load_all_entities()
    except Exception:
        pass

    return MetaRegistry.get(entity)


# =============================================================================
# get_doc
# =============================================================================

async def get_doc(
    entity: str,
    id: str,
    db: AsyncSession,
    as_dict: bool = False
) -> Optional[Any]:
    """Fetch a document by entity name and ID."""
    model = _get_model(entity)
    if not model:
        return None

    result = await db.execute(select(model).where(model.id == id))
    doc = result.scalar_one_or_none()

    if doc and as_dict:
        return _record_to_dict(doc)

    return doc


# =============================================================================
# get_value
# =============================================================================

async def get_value(
    entity: str,
    filters: Union[str, dict],
    fieldname: Union[str, list[str]],
    db: AsyncSession,
    as_dict: bool = False
) -> Optional[Any]:
    """Get a single field value or multiple field values."""
    model = _get_model(entity)
    if not model:
        return None

    query = select(model)

    if isinstance(filters, str):
        query = query.where(model.id == filters)
    elif isinstance(filters, dict):
        for field, value in filters.items():
            if hasattr(model, field):
                condition = build_filter_condition(getattr(model, field), value)
                if condition is not None:
                    query = query.where(condition)

    result = await db.execute(query)
    doc = result.scalar_one_or_none()

    if not doc:
        return None

    if fieldname == "*":
        return _record_to_dict(doc)

    if isinstance(fieldname, str):
        return getattr(doc, fieldname, None)

    if isinstance(fieldname, list):
        if as_dict:
            return {f: getattr(doc, f, None) for f in fieldname}
        return tuple(getattr(doc, f, None) for f in fieldname)

    return None


# =============================================================================
# get_list
# =============================================================================

async def get_list(
    entity: str,
    filters: Optional[dict] = None,
    fields: Union[str, list[str]] = "*",
    db: AsyncSession = None,
    limit: int = 0,
    order_by: Optional[str] = None,
    as_dict: bool = True
) -> list[Any]:
    """Fetch a list of documents matching filters."""
    model = _get_model(entity)
    if not model:
        return []

    query = select(model)

    if filters:
        for field, value in filters.items():
            if hasattr(model, field):
                condition = build_filter_condition(getattr(model, field), value)
                if condition is not None:
                    query = query.where(condition)

    if order_by and hasattr(model, order_by):
        query = query.order_by(getattr(model, order_by))

    if limit > 0:
        query = query.limit(limit)

    result = await db.execute(query)
    docs = result.scalars().all()

    if not as_dict:
        return docs

    out = []
    for doc in docs:
        if fields == "*":
            out.append(_record_to_dict(doc))
        elif isinstance(fields, list):
            item = {}
            for f in fields:
                item[f] = getattr(doc, f, None)
            out.append(item)

    return out
