"""
Print Assembler Loader
=======================
Auto-registers all entity-specific print data assemblers.
Called once during app startup or on first print request.
"""
from app.infrastructure.print.registry import register_assembler


_loaded = False


def load_print_assemblers() -> None:
    """Register all known print data assemblers. Idempotent."""
    global _loaded
    if _loaded:
        return

    _loaded = True
