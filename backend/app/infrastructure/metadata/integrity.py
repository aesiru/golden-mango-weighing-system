"""Metadata and model integrity checks for setup and fresh installs."""

from __future__ import annotations

from app.infrastructure.database.repositories.entity_repository import get_entity_model
from app.meta.registry import MetaRegistry


def _field_target_name(field) -> str | None:
    if field.field_type == "link":
        return field.link_entity
    if field.field_type == "parent_child_link":
        return field.child_entity
    return None


def validate_loaded_metadata_and_models() -> None:
    """Raise a RuntimeError if loaded entity metadata and models are inconsistent.

    This guards against the class of install failures caused by metadata/model drift,
    such as link_entity values that do not resolve to a loaded entity or model
    foreign keys that point to the wrong table name.
    """
    entity_map = {entity.name: entity for entity in MetaRegistry.list_all()}
    problems: list[str] = []

    for entity in entity_map.values():
        model = get_entity_model(entity.name)
        if model is None:
            problems.append(f"Entity '{entity.name}' has no registered SQLAlchemy model")
            continue

        table = getattr(model, "__table__", None)
        if table is None:
            problems.append(f"Entity '{entity.name}' model has no __table__")
            continue

        for field in entity.fields:
            target_name = _field_target_name(field)
            if not target_name:
                continue

            target_entity = entity_map.get(target_name)
            if target_entity is None:
                problems.append(
                    f"Entity '{entity.name}' field '{field.name}' references missing entity '{target_name}'"
                )
                continue

            column = table.columns.get(field.name)
            if column is None:
                problems.append(
                    f"Entity '{entity.name}' model is missing column '{field.name}'"
                )
                continue

            if field.field_type not in {"link", "parent_child_link"}:
                continue

            expected_target = f"{target_entity.table_name}.id"
            fk_targets = sorted(fk.target_fullname for fk in column.foreign_keys)
            if fk_targets and expected_target not in fk_targets:
                problems.append(
                    f"Entity '{entity.name}' field '{field.name}' should reference '{expected_target}' but has {fk_targets}"
                )

    if problems:
        detail = "\n  - ".join(problems)
        raise RuntimeError(f"Metadata/model integrity check failed:\n  - {detail}")