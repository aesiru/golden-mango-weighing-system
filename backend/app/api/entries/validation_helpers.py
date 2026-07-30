"""
Validation Helper Functions

Shared utilities for humanizing validation errors and building user-friendly error messages.
This module follows SOLID principles by providing reusable, single-purpose functions.

Clean Architecture Layer: API / Shared Utilities
"""
from typing import Any


def _humanize_field_name(field_name: Any, meta: Any) -> str:
    """Return a user-facing label for a field key."""
    field_key = str(field_name)
    field_meta = next((f for f in (meta.fields or []) if f.name == field_key), None)
    if field_meta and field_meta.label:
        return field_meta.label
    return field_key.replace("_", " ").title()


def _humanize_pydantic_error(err: Any, label: str, field_required: bool) -> str:
    """Convert a raw Pydantic error dict into a user-friendly message."""
    err_type = err.get("type", "")
    # Missing / null on a required field
    if err_type in ("missing", "none_required"):
        return f"{label} is required"
    # None sent for a non-nullable field — same user-facing meaning as missing
    if err_type == "string_type" and field_required:
        return f"{label} is required"
    # Empty string on a min_length=1 field
    if err_type == "string_too_short":
        return f"{label} cannot be empty"
    # Type coercion failures for optional fields
    if err_type in ("string_type", "string_pattern_mismatch"):
        return f"{label} must be a valid text value"
    if err_type in ("int_type", "int_parsing"):
        return f"{label} must be a whole number"
    if err_type in ("float_type", "float_parsing"):
        return f"{label} must be a number"
    if err_type in ("bool_type", "bool_parsing"):
        return f"{label} must be true or false"
    if err_type in ("date_type", "date_from_datetime_parsing", "date_parsing"):
        return f"{label} must be a valid date"
    if err_type in ("datetime_type", "datetime_parsing"):
        return f"{label} must be a valid date and time"
    if err_type == "value_error":
        ctx = err.get("ctx", {})
        return f"{label}: {ctx.get('error', err.get('msg', 'Invalid value'))}"
    # Fallback — strip Pydantic boilerplate prefixes and sentence-case
    raw = err.get("msg", "Invalid value")
    raw = raw.removeprefix("Value error, ").removeprefix("Assertion failed, ")
    return f"{label}: {raw[0].upper()}{raw[1:]}" if raw else f"{label}: Invalid value"


def _build_validation_message(error_map: dict[str, Any], meta: Any) -> str:
    """Build a top-level, human-readable validation failure message."""
    labels = [_humanize_field_name(key, meta) for key in error_map.keys()]
    return f"Validation failed: {', '.join(labels)}"


def extract_field_label_from_error(error_msg: str, field_name: str) -> str:
    """
    Extract a human-readable field label from an error message.
    
    Handles formats like:
    - "Field Label is required" -> "Field Label"
    - "Field Label: error message" -> "Field Label"
    - Falls back to title-cased field name if no pattern matches
    """
    if " is required" in error_msg:
        return error_msg.replace(" is required", "")
    elif ": " in error_msg:
        return error_msg.split(": ")[0]
    else:
        return field_name.replace("_", " ").title()
