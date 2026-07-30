"""Module contract helpers for core framework integration."""
from typing import Dict, Any, List, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ModuleContract:
    """Utility contract for module validation and framework access."""
    
    _framework_contracts_registered: bool = False
    _registered_core_entities: List[str] = []
    
    @staticmethod
    def initialize_module(module_name: str, module_path: str) -> None:
        """Initialize a module with Core Framework integration.
        
        Args:
            module_name: Name of the module (e.g., 'core' or 'my_module')
            module_path: Path to module directory
            
        This function is called by the module loader during application startup.
        """
        from app.core.framework import initialize_core_framework
        from app.meta.registry import MetaRegistry
        
        # Ensure core framework is initialized first
        initialize_core_framework()
        
        # Load module entities
        module_entities = ModuleContract._load_module_entities(module_path)
        
        # Register with global registry
        for entity_name, entity_meta in module_entities.items():
            entity_meta.is_system = False  # Mark as module entity
            MetaRegistry.register(entity_meta)
        
        logger.info(f"Initialized module '{module_name}' with {len(module_entities)} entities")
    
    @staticmethod
    def _load_module_entities(module_path: str) -> Dict[str, Any]:
        """Load entity metadata from module's entities directory."""
        from app.entities import load_entity_from_json
        
        entities = {}
        entities_dir = Path(module_path) / "entities"
        
        if not entities_dir.exists():
            logger.warning(f"No entities directory found in {module_path}")
            return entities
        
        json_files = list(entities_dir.glob("*.json"))
        json_files.extend(
            nested_json
            for nested_json in entities_dir.glob("*/*.json")
            if nested_json.parent.name == nested_json.stem
        )

        for json_file in sorted(set(json_files)):
            entity_name = json_file.stem
            try:
                entity_meta = load_entity_from_json(json_file, module_name=Path(module_path).name)
                if entity_meta is None:
                    continue
                entities[entity_name] = entity_meta
                logger.debug(f"Loaded module entity: {entity_name}")
            except Exception as e:
                logger.error(f"Failed to load module entity {entity_name}: {e}")
        
        return entities
    
    @staticmethod
    def get_core_entity(entity_name: str) -> Optional[Any]:
        """Get a core entity by name.
        
        Modules should use this method to access core entities
        rather than importing them directly.
        """
        from app.core.framework import get_core_entity
        return get_core_entity(entity_name)
    
    @staticmethod
    def list_core_entities() -> List[str]:
        """List all available core entities."""
        from app.core.framework import list_core_entities
        return list_core_entities()
    
    @staticmethod
    def register_framework_contracts(core_entities: Optional[List[str]] = None) -> None:
        """Register framework contracts for module use."""
        ModuleContract._framework_contracts_registered = True
        ModuleContract._registered_core_entities = sorted(core_entities or [])
        logger.debug("Framework contracts registered")

    @staticmethod
    def framework_contracts_registered() -> bool:
        """Check whether the framework contract registry is ready."""
        return ModuleContract._framework_contracts_registered

    @staticmethod
    def get_registered_core_entities() -> List[str]:
        """Get the core entity names published to modules."""
        return list(ModuleContract._registered_core_entities)
    
    @staticmethod
    def validate_module_structure(module_path: str) -> List[str]:
        """Validate that a module follows the expected structure.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        module_dir = Path(module_path)
        
        # Check for required directories
        required_dirs = ['entities', 'models']
        for required_dir in required_dirs:
            if not (module_dir / required_dir).exists():
                errors.append(f"Missing required directory: {required_dir}")
        
        # Check for at least one entity
        entities_dir = module_dir / 'entities'
        if entities_dir.exists():
            json_files = list(entities_dir.glob("*.json"))
            if not json_files:
                errors.append("No entity JSON files found in entities directory")
        
        return errors
    
    @staticmethod
    def get_module_info(module_path: str) -> Dict[str, Any]:
        """Get information about a module."""
        module_dir = Path(module_path)
        entities_dir = module_dir / 'entities'
        
        entity_count = 0
        if entities_dir.exists():
            entity_count = len(list(entities_dir.glob("*.json")))
        
        return {
            'name': module_dir.name,
            'path': str(module_dir),
            'entity_count': entity_count,
            'has_models': (module_dir / 'models').exists(),
            'has_apis': (module_dir / 'apis').exists(),
            'has_hooks': (module_dir / 'hooks.py').exists(),
        }
