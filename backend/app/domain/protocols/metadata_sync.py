"""
Metadata Sync Protocol
======================
Abstract interface for the metadata synchronization system.
Defines the contract for atomic metadata save operations
(Frappe-inspired: validate → save JSON → reload registry → update model → migrate DB).
"""
from typing import Protocol, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ChangeType(str, Enum):
    SAFE = "safe"
    DANGEROUS = "dangerous"


@dataclass
class FieldChange:
    """Represents a single change to a field."""
    field_name: str
    change_type: ChangeType
    description: str
    old_value: Any = None
    new_value: Any = None


@dataclass
class ChangeAnalysis:
    """Result of analyzing changes between current and new metadata."""
    entity_name: str
    changes: list[FieldChange] = field(default_factory=list)
    is_safe: bool = True

    def add_change(self, change: FieldChange):
        self.changes.append(change)
        if change.change_type == ChangeType.DANGEROUS:
            self.is_safe = False


@dataclass
class SyncResult:
    """Result of an atomic metadata sync operation."""
    success: bool
    message: str
    entity_name: str = ""
    # What was done
    json_saved: bool = False
    registry_reloaded: bool = False
    model_updated: bool = False
    migration_generated: bool = False
    migration_applied: bool = False
    # Details
    changes: Optional[ChangeAnalysis] = None
    backup_path: Optional[str] = None
    model_path: Optional[str] = None
    migration_file: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class MetadataReaderProtocol(Protocol):
    """Read-only operations on entity metadata JSON files."""

    def list_all_entities(self) -> list[dict]:
        """List all entities with summary info."""
        ...

    def get_entity_metadata(self, entity_name: str) -> Optional[dict]:
        """Get full metadata dict for an entity."""
        ...

    def get_entity_json_path(self, entity_name: str) -> Optional[Any]:
        """Get the filesystem path to an entity's JSON file."""
        ...


class MetadataWriterProtocol(Protocol):
    """Write operations on entity metadata JSON files."""

    def save_metadata(self, entity_name: str, metadata: dict) -> str:
        """Save metadata to JSON file. Returns the file path."""
        ...

    def create_backup(self, entity_name: str) -> Optional[str]:
        """Create a backup of current metadata. Returns backup path."""
        ...

    def list_backups(self, entity_name: str) -> list[dict]:
        """List available backups for an entity."""
        ...

    def restore_backup(self, entity_name: str, backup_filename: str) -> dict:
        """Restore metadata from a backup."""
        ...


class MetadataValidatorProtocol(Protocol):
    """Validates entity metadata structure and values."""

    def validate(self, metadata: dict) -> tuple[bool, list[str]]:
        """Validate metadata. Returns (is_valid, errors)."""
        ...


class ChangeAnalyzerProtocol(Protocol):
    """Analyzes changes between current and new metadata."""

    def analyze(self, entity_name: str, new_metadata: dict) -> ChangeAnalysis:
        """Compare current vs new metadata and categorize changes."""
        ...


class ModelGeneratorProtocol(Protocol):
    """Generates and updates SQLAlchemy model files from metadata."""

    def generate_model_code(self, metadata: dict) -> str:
        """Generate SQLAlchemy model code from metadata."""
        ...

    def update_model_file(self, metadata: dict, backup: bool = True, **kwargs) -> dict:
        """Update or create the model file. Returns result dict."""
        ...

    def get_model_diff(self, metadata: dict, **kwargs) -> dict:
        """Get diff between current model and what would be generated."""
        ...


class MigrationManagerProtocol(Protocol):
    """Manages database migrations."""

    def generate_migration(self, message: str) -> dict:
        """Generate an Alembic migration. Returns result dict."""
        ...

    def apply_migration(self, revision: str = "head") -> dict:
        """Apply migrations up to a revision. Returns result dict."""
        ...

    def rollback_migration(self, steps: int = 1) -> dict:
        """Rollback N migrations. Returns result dict."""
        ...

    def get_current_revision(self) -> dict:
        """Get current DB revision."""
        ...

    def get_pending_migrations(self) -> dict:
        """Get migration history with pending status."""
        ...

    def check_migration_needed(self) -> dict:
        """Check if schema changes need migration."""
        ...


class RegistryManagerProtocol(Protocol):
    """Manages the in-memory MetaRegistry."""

    def reload_entity(self, entity_name: str, json_path: Any) -> bool:
        """Reload a single entity into the registry. Returns success."""
        ...

    def reload_all(self) -> int:
        """Reload all entities. Returns count loaded."""
        ...
