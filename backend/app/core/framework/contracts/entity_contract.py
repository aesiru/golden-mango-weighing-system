"""Entity contract utilities for core framework metadata and model registration."""
from typing import Dict, Any, List
from dataclasses import dataclass

@dataclass
class EntityCapabilities:
    """Defines what an entity can do within the system."""
    can_create: bool = True
    can_read: bool = True
    can_update: bool = True
    can_delete: bool = True
    can_workflow: bool = False
    can_attach: bool = False
    can_audit: bool = False

class EntityContract:
    """Runtime contract registry for core framework entities."""
    
    _core_entities: Dict[str, Any] = {}
    _core_models: Dict[str, Any] = {}
    
    @classmethod
    def register_core_entities(cls, entities: Dict[str, Any]) -> None:
        """Register core entities with the contract system."""
        cls._core_entities = dict(sorted(entities.items()))

    @classmethod
    def register_core_models(cls, models: Dict[str, Any]) -> None:
        """Register SQLAlchemy models for core entities."""
        cls._core_models = dict(sorted(models.items()))

    @classmethod
    def get_core_entity_metadata(cls, entity_name: str) -> Any | None:
        """Get registered metadata for a core entity."""
        return cls._core_entities.get(entity_name)

    @classmethod
    def get_core_model(cls, entity_name: str) -> Any | None:
        """Get registered SQLAlchemy model for a core entity."""
        return cls._core_models.get(entity_name)

    @classmethod
    def reset(cls) -> None:
        """Reset registered entities and models."""
        cls._core_entities.clear()
        cls._core_models.clear()

    @staticmethod
    def _resolve_rbac_operations(entity_meta: Any) -> set[str]:
        rbac = getattr(entity_meta, "rbac", {}) or {}
        if not isinstance(rbac, dict) or not rbac:
            return {"read", "create", "update", "delete"}

        operations: set[str] = set()
        for rights in rbac.values():
            if not isinstance(rights, list):
                continue
            if "*" in rights:
                return {"read", "create", "update", "delete"}
            operations.update(str(right).lower() for right in rights)
        return operations
    
    @classmethod
    def get_core_capabilities(cls, entity_name: str) -> EntityCapabilities:
        """Get capabilities for a core entity."""
        if entity_name not in cls._core_entities:
            return EntityCapabilities()
        
        entity_meta = cls._core_entities[entity_name]
        operations = cls._resolve_rbac_operations(entity_meta)
        
        return EntityCapabilities(
            can_create="create" in operations,
            can_read="read" in operations,
            can_update="update" in operations,
            can_delete="delete" in operations,
            can_workflow=bool(entity_meta.workflow),
            can_attach=entity_meta.attachment_config is not None,
            can_audit=True  # All core entities support auditing
        )
    
    @classmethod
    def is_core_entity(cls, entity_name: str) -> bool:
        """Check if an entity is a core framework entity."""
        return entity_name in cls._core_entities
    
    @classmethod
    def list_core_entities(cls) -> List[str]:
        """List all registered core entities."""
        return list(cls._core_entities.keys())
    
    @classmethod
    def validate_entity_metadata(cls, entity_meta: Any) -> bool:
        """Validate minimal metadata requirements for framework registration."""
        if entity_meta is None:
            return False
        if not getattr(entity_meta, "name", None):
            return False
        if not getattr(entity_meta, "table_name", None):
            return False
        if not getattr(entity_meta, "is_system", False):
            return False
        return isinstance(getattr(entity_meta, "fields", None), list)

    @classmethod
    def get_entity_dependencies(cls, entity_name: str) -> List[str]:
        """Collect entity dependencies from field/link/child references."""
        entity_meta = cls.get_core_entity_metadata(entity_name)
        if entity_meta is None:
            return []

        dependencies: list[str] = []

        for field in getattr(entity_meta, "fields", []):
            for attr in ("link_entity", "child_entity", "parent_entity"):
                value = getattr(field, attr, None)
                if value and value not in dependencies:
                    dependencies.append(value)

        for link in getattr(entity_meta, "links", []):
            linked_entity = link.get("entity") if isinstance(link, dict) else None
            if linked_entity and linked_entity not in dependencies:
                dependencies.append(linked_entity)

        for child in getattr(entity_meta, "children", []):
            child_entity = getattr(child, "entity", None)
            if child_entity and child_entity not in dependencies:
                dependencies.append(child_entity)

        return dependencies
