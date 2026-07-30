<!-- SCOPE: Application service documentation for Frappe-inspired atomic metadata synchronization -->
<!-- DOC_KIND: reference -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Understanding metadata sync architecture, implementing atomic save operations, managing model generation -->
<!-- SKIP_WHEN: Quick API reference - use the Quick Navigation section -->
<!-- PRIMARY_SOURCES: backend/app/application/services/metadata_sync_service.py, backend/app/domain/protocols/metadata_sync.py, backend/app/infrastructure/metadata/ -->

# Metadata Sync Service

## Quick Navigation

- [Architecture](#architecture) - Clean Architecture compliance and protocols
- [API Endpoints](#api-endpoints) - Model editor REST API specifications
- [Atomic Save Operation](#atomic-save-operation) - 9-step sync process
- [Modes of Operation](#modes-of-operation) - Full sync, JSON-only, preview
- [Frontend Integration](#frontend-integration) - Model editor UI and migration status
- [Backup and Recovery](#backup-and-recovery) - Automatic backups and restore
- [Forge CLI Integration](#forge-cli-integration) - CLI command mapping
- [Testing](#testing) - Test strategies and coverage
- [Error Handling](#error-handling) - Validation and partial failure scenarios
- [Security](#security) - Admin access and audit logging
- [Performance](#performance) - File I/O and migration optimization

## Agent Entry

**Purpose**: The Metadata Sync Service provides Frappe-inspired atomic metadata synchronization. A single "save" operation atomically validates, backs up, saves JSON, reloads registry, updates SQLAlchemy models, generates Alembic migrations, and applies them to database. This eliminates desynchronization between entity definitions and actual database schema.

**When to Read**:

- Understanding atomic metadata sync architecture
- Implementing model editor operations
- Troubleshooting migration generation issues
- Learning about clean architecture protocols
- Managing entity metadata changes
- Understanding backup and recovery processes

**When to Skip**: Quick model editor API reference - use the Quick Navigation section above

**Canonical**: This is the primary reference for metadata sync service architecture and atomic operations

**Next**: Read Architecture section to understand clean design, then Atomic Save Operation for the 9-step process

**Primary Sources**:

- `backend/app/application/services/metadata_sync_service.py` - Core service implementation
- `backend/app/domain/protocols/metadata_sync.py` - Protocol definitions
- `backend/app/infrastructure/metadata/` - Adapter implementations

## Overview

The Metadata Sync Service provides Frappe-inspired atomic metadata synchronization. A single "save" operation atomically validates, backs up, saves JSON, reloads the registry, updates SQLAlchemy models, generates Alembic migrations, and applies them to the database. This eliminates desynchronization between entity definitions and the actual database schema.

## Architecture

### Clean Architecture Compliance

```
┌─────────────────────────────────────────────────────────────┐
│                    MetadataSyncService                      │
├─────────────────────────────────────────────────────────────┤
│  reader: MetadataReaderProtocol                             │
│  writer: MetadataWriterProtocol                               │
│  validator: MetadataValidatorProtocol                       │
│  analyzer: ChangeAnalyzerProtocol                             │
│  model_gen: ModelGeneratorProtocol                          │
│  migration: MigrationManagerProtocol                        │
│  registry: RegistryManagerProtocol                            │
└─────────────────────────────────────────────────────────────┘
```

**Protocols (Domain Layer):**

- `MetadataReaderProtocol`: Read entity metadata from JSON files
- `MetadataWriterProtocol`: Write JSON and create backups
- `MetadataValidatorProtocol`: Validate metadata structure
- `ChangeAnalyzerProtocol`: Analyze safe vs dangerous changes
- `ModelGeneratorProtocol`: Generate SQLAlchemy model files
- `MigrationManagerProtocol`: Generate and apply Alembic migrations
- `RegistryManagerProtocol`: Reload entities in MetaRegistry

### Sync Result

```python
@dataclass
class SyncResult:
    success: bool
    message: str
    entity_name: str
    json_saved: bool = False
    registry_reloaded: bool = False
    model_updated: bool = False
    model_path: Optional[str] = None
    migration_generated: bool = False
    migration_applied: bool = False
    migration_file: Optional[str] = None
    backup_path: Optional[str] = None
    changes: Optional[ChangeAnalysis] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
```

## API Endpoints

**Base:** `/api/v1/admin/model-editor`

| Endpoint                   | Method | Description                                     |
| -------------------------- | ------ | ----------------------------------------------- |
| `/entity/{entity}`         | GET    | Get entity metadata                             |
| `/entity/{entity}`         | PUT    | Save and sync entity (atomic)                   |
| `/entity/{entity}/preview` | POST   | Preview changes without saving                  |
| `/sync-pending`            | POST   | Sync all pending changes (like `bench migrate`) |
| `/migration-status`        | GET    | Get current migration status                    |
| `/apply-migrations`        | POST   | Apply pending migrations                        |
| `/rollback-migrations`     | POST   | Rollback N migrations                           |
| `/entity/{entity}/backups` | GET    | List entity backups                             |
| `/entity/{entity}/restore` | POST   | Restore from backup                             |

## Atomic Save Operation

### 9-Step Process

```python
def save_and_sync(entity_name: str, metadata: dict, auto_migrate: bool = True) -> SyncResult:
    # Step 1: Validate metadata structure
    # Step 2: Analyze changes (safe vs dangerous)
    # Step 3: Create backup of current JSON
    # Step 4: Save new JSON to disk
    # Step 5: Reload entity in MetaRegistry
    # Step 6: Update SQLAlchemy model file
    # Step 7: Generate Alembic migration
    # Step 8: Apply migration to database
    # Step 9: Return comprehensive SyncResult
```

### Change Analysis

**Safe Changes:**

- Adding new nullable fields
- Adding new fields with defaults
- Changing field labels
- Adding field options

**Dangerous Changes (Requiring Migration):**

- Adding non-nullable fields without defaults
- Removing fields (data loss)
- Changing field types
- Renaming fields
- Modifying indexes/constraints

### Model Update Exclusions

Some entities managed by global workflow engine:

```python
MODEL_UPDATE_EXCLUDE = {"workflow_state", "workflow_action"}
```

## Modes of Operation

### 1. Full Sync (Default)

JSON → Registry → Model → Migration → Apply

```python
result = service.save_and_sync("purchase_request", metadata, auto_migrate=True)
```

### 2. JSON-Only Save

For development: defer model/migration to restart

```python
result = service.save_json_only("purchase_request", metadata)
# Message: "JSON saved and registry reloaded.
#           Model update and migration deferred —
#           restart or run 'Sync All' to apply schema changes."
```

### 3. Sync Pending

Apply all accumulated changes at once:

```python
result = service.sync_pending()
# Returns: updated_models, migration_applied, migration_file
```

### 4. Preview Changes

Validate and preview without saving:

```python
preview = service.preview_changes("purchase_request", metadata)
# Returns: valid, is_safe, changes, model_has_changes
```

## Frontend Integration

### Model Editor Page

**Location:** `frontend/app/pages/model-editor/[entity].vue`

**Features:**

- Field editor panel (add/remove/edit fields)
- Entity settings (workflow, attachments, view modes)
- Migration status cards
- Visual workflow steps: Edit → Save → Update Model → Generate → Apply
- "Apply Migrations" button
- "How It Works" expandable guide

### Migration Status Display

```vue
<div class="migration-status">
  <UCard>
    <template #header>Model Status</template>
    <UBadge :color="modelStatus.has_changes ? 'warning' : 'success'">
      {{ modelStatus.has_changes ? 'Changes Pending' : 'Up to Date' }}
    </UBadge>
  </UCard>

  <UCard>
    <template #header>Migration Status</template>
    <div>Current: {{ migrationStatus.current_revision }}</div>
    <div>Pending: {{ migrationStatus.migrations.length }}</div>
  </UCard>
</div>
```

### Save with Feedback

```typescript
async function saveEntity() {
  const result = await entityApi.saveEntity(entityName, metadata);

  if (result.success) {
    toast.add({
      title: "Metadata Synced",
      description: result.message, // "JSON saved, registry reloaded, model updated, migration generated, migration applied"
      color: "success",
    });

    // Refresh migration status
    await loadMigrationStatus();
  } else {
    toast.add({
      title: "Sync Failed",
      description: result.errors.join(", "),
      color: "error",
    });
  }
}
```

## Backup and Recovery

### Automatic Backups

Every save creates a timestamped backup:

```
backups/metadata/purchase_request_20240315_143022.json
```

### Restore Operation

```python
result = service.restore_backup("purchase_request", "purchase_request_20240315_143022.json")
# Restores JSON and re-runs full sync
```

### Listing Backups

```python
backups = service.list_backups("purchase_request")
# Returns: [{"filename": "...", "created_at": "...", "size": 1234}]
```

## Forge CLI Integration

Commands use this service internally:

```bash
forge migrate                    # sync_pending()
forge migrate --generate-only    # generate migration
forge migrate --apply-only       # apply migration
forge migrate --rollback 2       # rollback 2 steps
forge update-model purchase_request  # update model file only
```

## Testing

**Architecture Tests:** `backend/tests/test_architecture.py`

- Protocol conformance
- Dependency injection
- Clean architecture boundaries

**Unit Tests:** `backend/tests/test_metadata_sync.py`

- Validation logic
- Change analysis
- Model generation
- Migration operations

**Integration Tests:**

- Full 9-step save_and_sync
- Backup and restore
- Error handling and rollback

## Error Handling

### Validation Failures

```python
is_valid, errors = validator.validate(metadata)
if not is_valid:
    return SyncResult(success=False, message="Validation failed", errors=errors)
```

### Partial Failures

Non-fatal steps log warnings but continue:

- Backup failure (proceeds without backup)
- Model update failure (JSON saved but model stale)
- Migration apply failure (generated but not applied)

### Fatal Failures

Stop immediately:

- JSON save failure (data loss risk)
- Validation failure

## Security

- Admin-only access to model editor
- RBAC check on all endpoints
- Audit logging for metadata changes
- Backup retention policies

## Performance

- File I/O optimized with async operations
- Migration generation can be slow (database introspection)
- Model updates are file writes (fast)
- Registry reload rebuilds in-memory cache

## Future Enhancements

- Field-level migration preview (show SQL)
- Batch field operations
- Migration conflict resolution
- Schema diff visualization
- Automated migration testing
- Blueprint/template entities
- Field change impact analysis (where is this field used?)

## Maintenance

**Update Triggers**:

- Metadata sync process changes
- New validation rules added
- Model generation updates
- Migration workflow modifications
- Clean architecture protocol changes
- Backup/restore process updates

**Verification**:

- Run `pytest tests/test_metadata_sync.py` - all tests must pass
- Run `pytest tests/test_architecture.py` - architecture tests must pass
- Test full 9-step save_and_sync operation
- Verify backup and restore functionality
- Test JSON-only save mode
- Validate migration generation and application
- Check model update exclusions
- Confirm change analysis accuracy

**Last Updated**: 2026-04-05
