"""
Core Layer: Feature Flags

Runtime feature toggles have been simplified to the base framework.
"""

def is_po_enabled() -> bool:
    """Purchase Order workflow support has been removed from the core framework."""
    return False
