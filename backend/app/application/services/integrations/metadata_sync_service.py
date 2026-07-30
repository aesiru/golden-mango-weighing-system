"""
Metadata Sync Service
=====================
Application-layer orchestrator for atomic metadata synchronization.

Inspired by Frappe's DocType save: a single "save" operation atomically:
  1. Validates metadata
  2. Analyzes changes (safe vs dangerous)
  3. Creates backup of current JSON
  4. Saves new JSON to disk
  5. Reloads entity in MetaRegistry (so /meta/{entity} serves fresh data)
  6. Updates SQLAlchemy model file (so Alembic can detect schema changes)
  7. Generates Alembic migration (if schema changed)
  8. Applies migration to database
  9. Returns comprehensive SyncResult

No manual steps. No desync possible.
"""
from typing import Optional

from app.domain.protocols.metadata_sync import (
    MetadataReaderProtocol,
    MetadataWriterProtocol,
    MetadataValidatorProtocol,
    ChangeAnalyzerProtocol,
    ModelGeneratorProtocol,
    MigrationManagerProtocol,
    RegistryManagerProtocol,
    SyncResult,
    ChangeAnalysis,
)


# These entities have models managed by the global workflow engine.
# Regenerating them can cause SQLAlchemy class-name collisions.
MODEL_UPDATE_EXCLUDE = {"workflow_state", "workflow_action"}


class MetadataSyncService:
    """
    Orchestrates atomic metadata synchronization.

    All dependencies are injected via constructor (DIP).
    This service contains NO infrastructure imports — only protocols.
    """

    def __init__(
        self,
        reader: MetadataReaderProtocol,
        writer: MetadataWriterProtocol,
        validator: MetadataValidatorProtocol,
        analyzer: ChangeAnalyzerProtocol,
        model_generator: ModelGeneratorProtocol,
        migration_manager: MigrationManagerProtocol,
        registry_manager: RegistryManagerProtocol,
    ):
        self._reader = reader
        self._writer = writer
        self._validator = validator
        self._analyzer = analyzer
        self._model_gen = model_generator
        self._migration = migration_manager
        self._registry = registry_manager

    # ------------------------------------------------------------------
    # Primary operation: atomic save + sync
    # ------------------------------------------------------------------

    def save_and_sync(
        self,
        entity_name: str,
        metadata: dict,
        *,
        auto_migrate: bool = True,
    ) -> SyncResult:
        """
        Atomic save: validate → backup → save JSON → reload registry
        → update model → generate migration → apply migration.

        Args:
            entity_name: The entity being saved.
            metadata: Full entity metadata dict from the editor.
            auto_migrate: If True, generate and apply migration automatically.

        Returns:
            SyncResult with details of every step performed.
        """
        result = SyncResult(
            success=False,
            message="",
            entity_name=entity_name,
        )

        # --- Step 1: Validate ---
        is_valid, errors = self._validator.validate(metadata)
        if not is_valid:
            result.message = "Validation failed"
            result.errors = errors
            return result

        # --- Step 2: Analyze changes ---
        changes = self._analyzer.analyze(entity_name, metadata)
        result.changes = changes

        # --- Step 3: Backup current JSON ---
        try:
            backup_path = self._writer.create_backup(entity_name)
            result.backup_path = backup_path
        except Exception as e:
            result.warnings.append(f"Backup failed (non-fatal): {e}")

        # --- Step 4: Save JSON ---
        try:
            json_path = self._writer.save_metadata(entity_name, metadata)
            result.json_saved = True
        except Exception as e:
            result.message = f"Failed to save JSON: {e}"
            result.errors.append(str(e))
            return result

        # --- Step 5: Reload entity in MetaRegistry ---
        try:
            entity_json_path = self._reader.get_entity_json_path(entity_name)
            if entity_json_path:
                reloaded = self._registry.reload_entity(entity_name, entity_json_path)
                result.registry_reloaded = reloaded
            else:
                result.warnings.append("Could not find JSON path for registry reload")
        except Exception as e:
            result.warnings.append(f"Registry reload failed (non-fatal): {e}")

        # --- Step 6: Update SQLAlchemy model file ---
        model_file_changed = False
        if entity_name not in MODEL_UPDATE_EXCLUDE:
            try:
                _json_path = self._reader.get_entity_json_path(entity_name)
                model_result = self._model_gen.update_model_file(
                    metadata, backup=True, json_path=_json_path,
                )
                if model_result.get("success"):
                    result.model_updated = True
                    result.model_path = model_result.get("model_path")
                    model_file_changed = not model_result.get("skipped", False)
                else:
                    result.warnings.append(
                        f"Model update failed: {model_result.get('error', 'unknown')}"
                    )
            except Exception as e:
                result.warnings.append(f"Model update failed (non-fatal): {e}")
        else:
            result.warnings.append(
                f"Skipped model update for '{entity_name}' (managed by workflow engine)"
            )

        # --- Step 7 & 8: Generate + Apply migration ---
        if auto_migrate and model_file_changed:
            # Check if there are actual schema changes
            try:
                needs_check = self._migration.check_migration_needed()
                needs_migration = needs_check.get("needs_migration", False)
            except Exception:
                needs_migration = True  # err on the side of generating

            if needs_migration:
                # Generate migration
                try:
                    gen_result = self._migration.generate_migration(
                        f"Auto-sync {entity_name}"
                    )
                    if gen_result.get("success"):
                        if not gen_result.get("no_changes"):
                            result.migration_generated = True
                            result.migration_file = gen_result.get("migration_file")

                            # Apply migration
                            try:
                                apply_result = self._migration.apply_migration("head")
                                if apply_result.get("success"):
                                    result.migration_applied = True
                                else:
                                    result.warnings.append(
                                        f"Migration apply failed: {apply_result.get('error', 'unknown')}"
                                    )
                            except Exception as e:
                                result.warnings.append(f"Migration apply failed: {e}")
                        else:
                            result.warnings.append("No schema changes detected")
                    else:
                        result.warnings.append(
                            f"Migration generation failed: {gen_result.get('error', 'unknown')}"
                        )
                except Exception as e:
                    result.warnings.append(f"Migration generation failed: {e}")

        # --- Done ---
        result.success = True
        result.message = self._build_summary(result)
        return result

    # ------------------------------------------------------------------
    # Draft save: JSON + registry only (like Frappe doctype edit)
    # ------------------------------------------------------------------

    def save_json_only(
        self,
        entity_name: str,
        metadata: dict,
    ) -> SyncResult:
        """
        Save JSON and reload registry only — no model file update, no migration.
        The model + migration sync is deferred to a restart or explicit sync call.
        This avoids the backend process interruption that occurs when model files change.
        """
        result = SyncResult(
            success=False,
            message="",
            entity_name=entity_name,
        )

        # Validate
        is_valid, errors = self._validator.validate(metadata)
        if not is_valid:
            result.message = "Validation failed"
            result.errors = errors
            return result

        # Backup
        try:
            backup_path = self._writer.create_backup(entity_name)
            result.backup_path = backup_path
        except Exception as e:
            result.warnings.append(f"Backup failed (non-fatal): {e}")

        # Save JSON
        try:
            self._writer.save_metadata(entity_name, metadata)
            result.json_saved = True
        except Exception as e:
            result.message = f"Failed to save JSON: {e}"
            result.errors.append(str(e))
            return result

        # Reload registry
        try:
            entity_json_path = self._reader.get_entity_json_path(entity_name)
            if entity_json_path:
                reloaded = self._registry.reload_entity(entity_name, entity_json_path)
                result.registry_reloaded = reloaded
        except Exception as e:
            result.warnings.append(f"Registry reload failed (non-fatal): {e}")

        result.success = True
        result.message = "JSON saved and registry reloaded. Model update and migration deferred — restart or run 'Sync All' to apply schema changes."
        return result

    # ------------------------------------------------------------------
    # Sync pending: apply model + migration for all changed entities
    # ------------------------------------------------------------------

    def sync_pending(self) -> dict:
        """
        Scan all entity JSONs, update model files where needed, then
        generate + apply a single migration for all accumulated changes.
        Like Frappe's `bench migrate`.
        """
        entities = self._reader.list_all_entities()
        updated_models = []
        warnings = []

        for ent in entities:
            ent_name = ent.get("name") if isinstance(ent, dict) else getattr(ent, "name", None)
            if not ent_name:
                continue
            if ent_name in MODEL_UPDATE_EXCLUDE:
                continue
            metadata = self._reader.get_entity_metadata(ent_name)
            if not metadata:
                continue
            try:
                _json_path = self._reader.get_entity_json_path(ent_name)
                model_result = self._model_gen.update_model_file(
                    metadata, backup=True, json_path=_json_path,
                )
                if model_result.get("success") and not model_result.get("skipped", False):
                    updated_models.append(ent_name)
            except Exception as e:
                warnings.append(f"{ent_name}: model update failed: {e}")

        # Reload registry
        try:
            self._registry.reload_all()
        except Exception as e:
            warnings.append(f"Registry reload failed: {e}")

        # Generate + apply migration if any models changed
        migration_applied = False
        migration_file = None
        if updated_models:
            try:
                needs_check = self._migration.check_migration_needed()
                if needs_check.get("needs_migration", False):
                    gen_result = self._migration.generate_migration(
                        f"Sync {len(updated_models)} entities"
                    )
                    if gen_result.get("success") and not gen_result.get("no_changes"):
                        migration_file = gen_result.get("migration_file")
                        apply_result = self._migration.apply_migration("head")
                        migration_applied = apply_result.get("success", False)
                        if not migration_applied:
                            warnings.append(f"Migration apply failed: {apply_result.get('error')}")
            except Exception as e:
                warnings.append(f"Migration failed: {e}")

        return {
            "success": True,
            "updated_models": updated_models,
            "migration_applied": migration_applied,
            "migration_file": migration_file,
            "warnings": warnings,
            "message": f"Synced {len(updated_models)} model(s). Migration {'applied' if migration_applied else 'not needed'}.",
        }

    # ------------------------------------------------------------------
    # Read-only operations (delegated)
    # ------------------------------------------------------------------

    def list_entities(self) -> list[dict]:
        """List all entities with summary info."""
        return self._reader.list_all_entities()

    def get_entity(self, entity_name: str) -> Optional[dict]:
        """Get full metadata for an entity."""
        return self._reader.get_entity_metadata(entity_name)

    def get_model_status(self, metadata: dict) -> dict:
        """Get model sync status for an entity."""
        return self._model_gen.get_model_diff(metadata)

    def preview_changes(self, entity_name: str, metadata: dict) -> dict:
        """Preview changes without saving."""
        is_valid, errors = self._validator.validate(metadata)
        if not is_valid:
            return {"valid": False, "errors": errors}

        changes = self._analyzer.analyze(entity_name, metadata)
        model_diff = self._model_gen.get_model_diff(metadata)

        return {
            "valid": True,
            "is_safe": changes.is_safe,
            "changes": [
                {
                    "field": c.field_name,
                    "type": c.change_type.value,
                    "description": c.description,
                }
                for c in changes.changes
            ],
            "model_has_changes": model_diff.get("has_changes", False),
        }

    # ------------------------------------------------------------------
    # Migration operations (delegated)
    # ------------------------------------------------------------------

    def get_migration_status(self) -> dict:
        """Get current migration status."""
        current = self._migration.get_current_revision()
        pending = self._migration.get_pending_migrations()
        needs = self._migration.check_migration_needed()
        return {
            "current_revision": current.get("revision") if current.get("success") else None,
            "migrations": pending.get("migrations", []) if pending.get("success") else [],
            "needs_migration": needs.get("needs_migration", False) if needs.get("success") else None,
        }

    def apply_migrations(self, revision: str = "head") -> dict:
        """Apply pending migrations."""
        return self._migration.apply_migration(revision)

    def rollback_migrations(self, steps: int = 1) -> dict:
        """Rollback N migrations."""
        return self._migration.rollback_migration(steps)

    # ------------------------------------------------------------------
    # Backup operations (delegated)
    # ------------------------------------------------------------------

    def list_backups(self, entity_name: str) -> list[dict]:
        """List backups for an entity."""
        return self._writer.list_backups(entity_name)

    def restore_backup(self, entity_name: str, backup_filename: str) -> SyncResult:
        """Restore a backup and re-sync everything."""
        restore_result = self._writer.restore_backup(entity_name, backup_filename)
        if not restore_result.get("success"):
            return SyncResult(
                success=False,
                message=restore_result.get("error", "Restore failed"),
                entity_name=entity_name,
            )

        # After restoring, reload the metadata and re-sync
        metadata = self._reader.get_entity_metadata(entity_name)
        if not metadata:
            return SyncResult(
                success=False,
                message="Restored JSON but could not read it back",
                entity_name=entity_name,
            )

        return self.save_and_sync(entity_name, metadata, auto_migrate=True)

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def reload_all_metadata(self) -> int:
        """Reload all entities into the registry."""
        return self._registry.reload_all()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_summary(result: SyncResult) -> str:
        """Build a human-readable summary of what was done."""
        parts = []
        if result.json_saved:
            parts.append("JSON saved")
        if result.registry_reloaded:
            parts.append("registry reloaded")
        if result.model_updated:
            parts.append("model updated")
        if result.migration_generated:
            parts.append("migration generated")
        if result.migration_applied:
            parts.append("migration applied")

        if parts:
            return f"Metadata synced: {', '.join(parts)}"
        return "Metadata saved (no schema changes)"
