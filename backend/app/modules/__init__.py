"""
Core Modules Package

This package contains all installable modules for the core application framework.
Each module is a self-contained unit with its own entities, models, and business logic.

Module Structure:
    app/modules/{module_name}/
        __init__.py          - Module registration
        entities/            - Entity metadata JSON and API files
            {entity}/
                {entity}.json
                {entity}.py  (optional hooks)
        models/              - SQLAlchemy models
            {entity}.py

Available Modules:
    - core: Core application framework and workflow engine.
"""

from pathlib import Path
from typing import List


def get_installed_modules() -> List[str]:
    """Get list of installed module names."""
    modules_dir = Path(__file__).parent
    modules = []
    
    for item in modules_dir.iterdir():
        if item.is_dir() and not item.name.startswith("_"):
            # Check if it has an __init__.py (valid Python package)
            if (item / "__init__.py").exists():
                modules.append(item.name)
    
    return sorted(modules)


def get_module_path(module_name: str) -> Path:
    """Get the path to a module directory."""
    return Path(__file__).parent / module_name
