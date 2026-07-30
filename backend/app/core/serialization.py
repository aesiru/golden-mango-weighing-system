"""
Core Layer: Serialization

Model-to-dict conversion with polymorphic field handling.

Clean Architecture Layer: Core
Responsibility: Provide serialization utilities for model conversion
"""
from typing import Any
from app.domain.protocols.serializable import Serializable


def record_to_dict(record: Any) -> dict:
    """Convert a SQLAlchemy model instance or dict to a serializable dict.

    Handles datetime serialization and supports both ORM objects and plain dicts.
    Objects implementing the Serializable protocol get priority.
    """
    def serialize_value(value: Any) -> Any:
        if isinstance(value, Serializable):
            return value.to_serializable()
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        elif isinstance(value, dict):
            return {k: serialize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [serialize_value(item) for item in value]
        return value

    # Serializable protocol takes priority
    if isinstance(record, Serializable):
        result = record.to_serializable()
        return result if isinstance(result, dict) else {"value": result}

    # SQLAlchemy model with __table__
    if hasattr(record, '__table__'):
        result = {}
        for column in record.__table__.columns:
            value = getattr(record, column.name)
            result[column.name] = serialize_value(value)
        return result

    # Generic object with __dict__
    if hasattr(record, '__dict__'):
        return {k: serialize_value(v) for k, v in record.__dict__.items() if not k.startswith('_')}

    # Already a dict
    if isinstance(record, dict):
        return {k: serialize_value(v) for k, v in record.items()}

    return {"value": serialize_value(record)}
