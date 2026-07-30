"""
Filter Builder
==============
Helper for building SQLAlchemy filter conditions.
Handles different value types (single values, lists, etc.) to generate appropriate SQL.
"""
from typing import Any
from sqlalchemy.sql import ColumnElement
from sqlalchemy.orm.attributes import InstrumentedAttribute


def build_filter_condition(
    field_attr: InstrumentedAttribute,
    value: Any
) -> ColumnElement | None:
    """
    Build a SQLAlchemy filter condition for a field and value.
    
    Args:
        field_attr: SQLAlchemy model field attribute
        value: Filter value (can be single value or list)
        
    Returns:
        SQLAlchemy condition or None if value is None/empty
        
    Examples:
        >>> build_filter_condition(model.name, "John")
        # Returns: model.name == 'John'
        
        >>> build_filter_condition(model.id, [1, 2, 3])
        # Returns: model.id IN (1, 2, 3)
    """
    if value is None:
        return None
    
    if isinstance(value, list):
        # Use IN operator for list values
        if value:  # Only apply if list is not empty
            return field_attr.in_(value)
        return None
    else:
        # Use equality operator for single values
        return field_attr == value
