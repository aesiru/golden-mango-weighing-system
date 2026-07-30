"""
Infrastructure Layer: Metadata Adapters (Shim)

Re-exports metadata adapters from split modules for backward compatibility.
This file maintains the original import path while delegating to the split modules.

Clean Architecture Layer: Infrastructure
Responsibility: Re-export metadata adapters from split modules
"""
from typing import Any
from app.infrastructure.metadata.reader import JsonMetadataReader
from app.infrastructure.metadata.writer import JsonMetadataWriter
from app.infrastructure.metadata.validator import (
    MetadataValidator,
    MetadataChangeAnalyzer,
    VALID_FIELD_TYPES,
)
from app.domain.protocols.metadata_sync import (
    MetadataReaderProtocol,
    MetadataWriterProtocol,
    MetadataValidatorProtocol,
    ChangeAnalyzerProtocol,
    ModelGeneratorProtocol,
    MigrationManagerProtocol,
    RegistryManagerProtocol,
)


class ModelGeneratorAdapter:
    """Wraps ModelGeneratorService to satisfy ModelGeneratorProtocol."""

    def __init__(self):
        from app.infrastructure.metadata.model_generator import ModelGeneratorService
        self._service = ModelGeneratorService()

    def generate_model_code(self, metadata: dict) -> str:
        return self._service.generate_model_code(metadata)

    def update_model_file(self, metadata: dict, backup: bool = True, **kwargs) -> dict:
        return self._service.update_model_file(metadata, backup=backup, **kwargs)

    def get_model_diff(self, metadata: dict, **kwargs) -> dict:
        return self._service.get_model_diff(metadata, **kwargs)


class MigrationManagerAdapter:
    """Wraps MigrationService to satisfy MigrationManagerProtocol."""

    def __init__(self):
        from app.infrastructure.metadata.migration_service import MigrationService
        self._service = MigrationService()

    def generate_migration(self, message: str) -> dict:
        return self._service.generate_migration(message)

    def apply_migration(self, revision: str = "head") -> dict:
        return self._service.apply_migration(revision)

    def rollback_migration(self, steps: int = 1) -> dict:
        return self._service.rollback_migration(steps)

    def get_current_revision(self) -> dict:
        return self._service.get_current_revision()

    def get_pending_migrations(self) -> dict:
        return self._service.get_pending_migrations()

    def check_migration_needed(self) -> dict:
        return self._service.check_migration_needed()


class RegistryManagerAdapter:
    """Manages the in-memory MetaRegistry."""

    def reload_entity(self, entity_name: str, json_path: Any) -> bool:
        from app.entities import load_entity_from_json
        from app.meta.schema_cache import load_or_build_schemas
        from app.meta.registry import MetaRegistry
        from pathlib import Path
        try:
            entity_json_path = Path(json_path)
            entity_meta = load_entity_from_json(entity_json_path)
            if entity_meta:
                MetaRegistry.register(entity_meta)
                # Keep schema registry in sync with metadata for runtime validation.
                write_schema, read_schema = load_or_build_schemas(entity_meta, entity_json_path)
                MetaRegistry.register_schema(entity_meta.name, write=write_schema, read=read_schema)
                return True
            return False
        except Exception as e:
            print(f"Warning: Failed to reload entity {entity_name}: {e}")
            return False

    def reload_all(self) -> int:
        from app.entities import load_all_entities
        from app.meta.registry import MetaRegistry
        MetaRegistry._entities.clear()
        load_all_entities()
        return len(MetaRegistry._entities)


__all__ = [
    "JsonMetadataReader",
    "JsonMetadataWriter",
    "MetadataValidator",
    "MetadataChangeAnalyzer",
    "VALID_FIELD_TYPES",
    "ModelGeneratorAdapter",
    "MigrationManagerAdapter",
    "RegistryManagerAdapter",
]
