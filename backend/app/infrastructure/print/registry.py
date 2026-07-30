"""
Print Assembler Registry
=========================
Central registry mapping entity names to their PrintDataAssembler implementations.
Follows OCP: add new assemblers without modifying existing code.
"""
from typing import Optional
from app.domain.protocols.print_assembler import PrintDataAssembler


_ASSEMBLERS: dict[str, PrintDataAssembler] = {}


def register_assembler(assembler: PrintDataAssembler) -> None:
    """Register a print data assembler for an entity."""
    _ASSEMBLERS[assembler.entity_name] = assembler


def get_assembler(entity_name: str) -> Optional[PrintDataAssembler]:
    """Get the registered assembler for an entity, or None for generic fallback."""
    return _ASSEMBLERS.get(entity_name)


def list_assemblers() -> list[str]:
    """List all entity names with registered assemblers."""
    return list(_ASSEMBLERS.keys())
