"""
Core Layer: Module Loader

Dynamic discovery and import of business modules.

Clean Architecture Layer: Core
Responsibility: Provide dynamic module loading functionality
"""
import importlib
import pkgutil
from pathlib import Path
import app.modules

# Module load order - modules listed first are loaded first
# This ensures dependencies are satisfied
MODULE_LOAD_ORDER = [
    "core",
    # All business modules removed - starting with barebones framework
    # Future modules can be added here in dependency order
]

def load_modules():
    """
    Dynamically load all modules in app/modules.
    This ensures SQLAlchemy models are registered with the Base metadata
    before the database is initialized.
    """
    # Initialize core framework FIRST before loading any modules
    # This ensures all core entities (User, Role, WorkflowState, etc.)
    # are available for modules to reference during their initialization
    from app.core.framework import initialize_core_framework
    initialize_core_framework()
    print("  Core framework initialized")
    
    modules_path = Path(app.modules.__file__).parent
    
    # Get all available modules
    available_modules = {m.name for m in pkgutil.iter_modules([str(modules_path)]) if not m.name.startswith("_")}
    
    # Load modules in order, then any remaining modules
    ordered_modules = [m for m in MODULE_LOAD_ORDER if m in available_modules]
    remaining_modules = sorted(available_modules - set(ordered_modules))
    all_modules = ordered_modules + remaining_modules
    
    # Iterate through modules in order
    for module_name in all_modules:
            
        # Try to import the models package for each module
        # e.g., app.modules.todo.models
        models_module = f"app.modules.{module_name}.models"
        try:
            importlib.import_module(models_module)
            print(f"  ✅ Loaded module: {module_name}")
        except ImportError:
            # It's okay if a module doesn't have a models package
            pass
        except Exception as e:
            print(f"  ⚠️  Error loading module {module_name}: {e}")
        
        # Try to load hooks for each module
        hooks_module = f"app.modules.{module_name}.hooks"
        try:
            hooks_mod = importlib.import_module(hooks_module)
            if hasattr(hooks_mod, 'register_hooks'):
                hooks_mod.register_hooks()
                print(f"  ✅ Registered hooks: {module_name}")
        except ImportError:
            # It's okay if a module doesn't have hooks
            pass
        except Exception as e:
            print(f"  ⚠️  Error loading hooks for {module_name}: {e}")
