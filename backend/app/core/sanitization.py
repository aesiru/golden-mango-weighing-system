"""
Core Layer: Input Sanitization

XSS prevention via regex-based string cleaning.

Clean Architecture Layer: Core
Responsibility: Provide input sanitization utilities
"""
import re
from typing import Any

# Tags that are never allowed in user input
_DANGEROUS_TAGS_RE = re.compile(
    r"<\s*/?\s*(script|iframe|object|embed|form|input|button|link|style|meta|base|applet)"
    r"[^>]*>",
    re.IGNORECASE,
)

# Event handler attributes (onclick, onerror, etc.)
_EVENT_ATTRS_RE = re.compile(
    r"\s+on\w+\s*=\s*[\"'][^\"']*[\"']",
    re.IGNORECASE,
)

# javascript: / data: URI schemes in href/src
_DANGEROUS_URI_RE = re.compile(
    r"(href|src|action)\s*=\s*[\"']\s*(javascript|data|vbscript)\s*:",
    re.IGNORECASE,
)


def sanitize_string(value: str) -> str:
    """Remove dangerous HTML constructs from a string value."""
    if not value:
        return value
    result = _DANGEROUS_TAGS_RE.sub("", value)
    result = _EVENT_ATTRS_RE.sub("", result)
    result = _DANGEROUS_URI_RE.sub("", result)
    return result


def sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize all string values in a flat dict (one level deep)."""
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        else:
            sanitized[key] = value
    return sanitized
