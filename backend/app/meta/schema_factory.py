"""
Meta Layer: Schema Factory
===========================
Builds Pydantic write/read schemas at startup from EntityMeta definitions.

Two schemas are generated per entity:
  - Write schema  (POST / PUT):  only writable fields, with required/optional
                                 enforcement derived from FieldMeta.
  - Read schema   (GET):         adds system fields (id, created_at, updated_at)
                                 and treats link fields as plain strings (title).

Usage (called from app.core.loader at startup)::

    from app.meta.schema_factory import build_write_schema, build_read_schema

    write_cls = build_write_schema(entity_meta)
    read_cls  = build_read_schema(entity_meta)

Validation (called in entity_crud.py)::

    from app.meta.registry import MetaRegistry
    schema = MetaRegistry.get_write_schema(entity_name)
    if schema:
        validated = schema.model_validate(data)
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, create_model

from app.meta.registry import EntityMeta, FieldMeta

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Field-type → Python type mapping
# ---------------------------------------------------------------------------

# Scalar field types that map 1-to-1 to a Python/Pydantic type.
_FIELD_TYPE_MAP: dict[str, type] = {
    "string": str,
    "str": str,
    "text": str,
    "textarea": str,
    "richtext": str,
    "rich_text": str,
    "email": str,
    "phone": str,
    "url": str,
    "password": str,
    "integer": int,
    "int": int,
    "float": float,
    "number": float,
    "currency": Decimal,
    "percent": float,
    "boolean": bool,
    "bool": bool,
    "date": date,
    "datetime": datetime,
    "time": str,
    # File / image uploads are stored as string paths/keys
    "attach": str,
    "image": str,
    "file": str,
    "attach_image": str,
    # Link / select fields resolve to str (foreign key or option value)
    "link": str,
    "select": str,
    "multiselect": str,
    "data": str,
}

# Fields that are always managed by the server and must never be accepted
# from client payloads on write.
_SERVER_MANAGED_FIELDS = frozenset(
    {
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "last_modified_by",
        "workflow_state",
        "row_no",
    }
)


def _resolve_python_type(field: FieldMeta) -> type:
    """Return the Python type for a FieldMeta, defaulting to ``Any``."""
    return _FIELD_TYPE_MAP.get(field.field_type.lower(), Any)


def _is_write_excluded(field: FieldMeta) -> bool:
    """Return True if the field should be excluded from the write schema."""
    if field.name in _SERVER_MANAGED_FIELDS:
        return True
    # Computed fields are read-only by definition
    if field.computed_from:
        return True
    # Explicitly readonly fields carry no client payload meaning
    if field.readonly:
        return True
    return False


def _build_field_definition(
    field: FieldMeta,
    *,
    for_update: bool = False,
) -> tuple[type, Any]:
    """
    Return a (annotation, default) tuple for ``pydantic.create_model``.

    Rules:
    - Required on create  → annotation is ``<type>``,          default is ``...``
    - Optional on create  → annotation is ``Optional[<type>]``, default is ``None``
    - On update all fields are optional (partial update semantics).

    Note: ``select`` field options are intentionally NOT validated as
    ``Literal[...]``.  Options are UI hints for dropdowns; stored values may
    legitimately differ (legacy data, API integrations, etc.).  Value
    validation is the responsibility of entity hooks, not the type layer.
    """
    py_type = _resolve_python_type(field)

    if for_update or not field.required:
        # Optional — wrap in Optional so None is accepted
        annotation = Optional[py_type]  # type: ignore[assignment]
        default: Any = None
        pydantic_field = Field(default=default, description=field.label)
    else:
        # Required — PEP 484 bare type, default = Ellipsis (required)
        annotation = py_type
        default = ...
        # For required string fields also reject empty strings
        if py_type == str:
            pydantic_field = Field(default=default, description=field.label, min_length=1)
        else:
            pydantic_field = Field(default=default, description=field.label)
    return annotation, pydantic_field


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_write_schema(entity_meta: EntityMeta) -> type[BaseModel]:
    """
    Build a strict Pydantic *write* schema from ``entity_meta``.

    Only writable, non-server-managed fields are included.
    Required fields use ``...`` as the default value; others default to ``None``.
    """
    field_definitions: dict[str, Any] = {}

    for f in entity_meta.fields:
        if _is_write_excluded(f):
            continue
        annotation, pydantic_field = _build_field_definition(f)
        field_definitions[f.name] = (annotation, pydantic_field)

    model_name = f"{entity_meta.name.title().replace('_', '')}WriteSchema"

    try:
        return create_model(model_name, **field_definitions)  # type: ignore[call-overload]
    except Exception:
        logger.exception("Failed to build write schema for '%s'", entity_meta.name)
        # Fallback: permissive model that accepts any dict
        return create_model(model_name)  # type: ignore[call-overload]


def build_read_schema(entity_meta: EntityMeta) -> type[BaseModel]:
    """
    Build a Pydantic *read* schema from ``entity_meta``.

    Includes all writable fields as optional, plus the standard system fields:
    ``id``, ``created_at``, ``updated_at``.  Link fields are ``Optional[str]``
    (they carry the display title, not a nested object).
    """
    field_definitions: dict[str, Any] = {
        "id": (str, Field(default=..., description="Record ID")),
        "created_at": (Optional[datetime], Field(default=None, description="Created timestamp")),
        "updated_at": (Optional[datetime], Field(default=None, description="Updated timestamp")),
    }

    for f in entity_meta.fields:
        if f.name in _SERVER_MANAGED_FIELDS:
            continue
        annotation, pydantic_field = _build_field_definition(f, for_update=True)
        field_definitions[f.name] = (annotation, pydantic_field)

    model_name = f"{entity_meta.name.title().replace('_', '')}ReadSchema"

    try:
        return create_model(model_name, **field_definitions)  # type: ignore[call-overload]
    except Exception:
        logger.exception("Failed to build read schema for '%s'", entity_meta.name)
        return create_model(model_name)  # type: ignore[call-overload]
