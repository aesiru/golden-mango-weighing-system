"""
Application Layer: Document Utilities

Consolidated helper functions for document operations.
Provides safe extraction and formatting utilities used across module APIs.

Clean Architecture Layer: Application
Responsibility: Provide utility functions for document data extraction and formatting
"""
from typing import Any

from app.meta.registry import MetaRegistry


def get_id(doc: Any) -> str | None:
    """Extract ID from doc (model instance or dict)."""
    return doc.id if hasattr(doc, 'id') else doc.get('id') if isinstance(doc, dict) else None


def get_attr(doc: Any, attr: str) -> Any:
    """Get attribute from model instance or dict."""
    if hasattr(doc, attr):
        return getattr(doc, attr)
    if isinstance(doc, dict):
        return doc.get(attr)
    return None


def to_float(val: Any) -> float:
    """Safely convert a value to float."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def to_int(val: Any) -> int:
    """Safely convert a value to int."""
    if val is None:
        return 0
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def display_label(*values: Any) -> str:
    """Return the first non-empty value as a string, or 'Unknown'."""
    for value in values:
        if value not in (None, "", False):
            return str(value)
    return "Unknown"


def meta_title_value(entity: str, doc: Any, fallback: Any = None) -> str:
    """Get the title field value from an entity document."""
    if doc is None:
        return display_label(fallback)
    meta = MetaRegistry.get(entity)
    title_field = meta.title_field if meta and getattr(meta, "title_field", None) else None
    if title_field:
        title_value = doc.get(title_field) if title_field and isinstance(doc, dict) else getattr(doc, title_field, None) if title_field else None
        doc_id = doc.get("id") if isinstance(doc, dict) else getattr(doc, "id", None)
        return display_label(title_value, doc_id, fallback)
    return display_label(fallback)


def fmt_qty(value: Any) -> str:
    """Format a quantity value, removing unnecessary decimal places."""
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return str(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.2f}".rstrip("0").rstrip(".")


def format_state_label(slug: str | None, workflow_def: dict[str, Any] | None = None) -> str:
    """Format a workflow state slug to a human-readable label.
    
    First tries to get the label from the workflow definition.
    Falls back to converting slug to title case (replacing underscores with spaces).
    
    Args:
        slug: The state slug (e.g., "pending_approval")
        workflow_def: Optional workflow definition dict containing states
        
    Returns:
        Human-readable label (e.g., "Pending Approval")
    """
    if not slug:
        return "Unknown"
    
    # Try to get label from workflow definition
    if workflow_def:
        for state in workflow_def.get("states", []):
            if state.get("slug") == slug:
                return state.get("label") or slug
    
    # Fallback to title case conversion
    return slug.replace("_", " ").title()


def normalize_state(value: Any) -> str:
    """Normalize workflow state to lowercase with underscores for case-insensitive comparison.
    
    Examples:
        'In Progress' -> 'in_progress'
        'Completed' -> 'completed'
        'Awaiting Resources' -> 'awaiting_resources'
    """
    if not value:
        return ""
    return str(value).strip().lower().replace(" ", "_")


def states_match(state1: Any, state2: Any) -> bool:
    """Check if two workflow states match (case-insensitive).
    
    Args:
        state1: First state to compare
        state2: Second state to compare
        
    Returns:
        True if states match (case-insensitive), False otherwise
        
    Examples:
        states_match('In Progress', 'in_progress') -> True
        states_match('Completed', 'COMPLETED') -> True
        states_match('Ready', 'closed') -> False
    """
    return normalize_state(state1) == normalize_state(state2)
