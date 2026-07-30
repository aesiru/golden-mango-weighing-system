"""Helpers for discovering core framework entity metadata files."""
from pathlib import Path

# This module will be used by the entity discovery system
# to find and load core framework entities

ENTITIES_DIR = Path(__file__).parent

def list_core_entities():
    """List all core framework entity JSON files."""
    return sorted(f.stem for f in ENTITIES_DIR.glob("*.json"))


def iter_entity_paths():
    """Iterate over framework entity JSON file paths."""
    yield from sorted(ENTITIES_DIR.glob("*.json"))

def get_entity_path(entity_name: str) -> Path:
    """Get the path to a core entity JSON file."""
    return ENTITIES_DIR / f"{entity_name}.json"

__all__ = ["ENTITIES_DIR", "list_core_entities", "iter_entity_paths", "get_entity_path"]
