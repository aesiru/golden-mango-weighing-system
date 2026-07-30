<!-- SCOPE: Application service documentation for CSV/Excel import and export operations -->
<!-- DOC_KIND: reference -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Understanding import/export architecture, implementing bulk data operations, managing validation -->
<!-- SKIP_WHEN: Quick API reference - use the Quick Navigation section -->
<!-- PRIMARY_SOURCES: backend/app/application/services/import_export_service.py, backend/app/api/routes/import_export.py, backend/app/core/config.py -->

# Import/Export Service

## Quick Navigation

- [Architecture](#architecture) - Service design and domain model
- [API Endpoints](#api-endpoints) - Import/export REST API specifications
- [Core Operations](#core-operations) - Validation and execution flows
- [Frontend Integration](#frontend-integration) - Import dialog and export functionality
- [Entity List Integration](#entity-list-integration) - Toolbar integration
- [Validation Rules](#validation-rules) - Header, row, and data type validation
- [Duplicate Detection](#duplicate-detection) - Create and update mode handling
- [Error Reporting](#error-reporting) - Error format and scenarios
- [Testing](#testing) - Test strategies and coverage
- [Security](#security) - RBAC and file validation
- [Configuration](#configuration) - Limits and batch processing

## Agent Entry

**Purpose**: The Import/Export Service orchestrates data import operations from CSV/Excel files with validation and duplicate detection. It supports both "create" mode (insert new records) and "update" mode (modify existing records by ID), making bulk data operations safe and predictable.

**When to Read**:

- Implementing bulk data import functionality
- Understanding validation and duplicate detection
- Configuring import/export operations
- Troubleshooting data import issues
- Building import UI components
- Managing file processing and limits

**When to Skip**: Quick import/export API reference - use the Quick Navigation section above

**Canonical**: This is the primary reference for import/export service architecture and bulk operations

**Next**: Read Architecture section to understand domain model, then API Endpoints for integration details

**Primary Sources**:

- `backend/app/application/services/import_export_service.py` - Core service implementation
- `backend/app/api/routes/import_export.py` - Import/export API endpoints
- `backend/app/core/config.py` - Configuration and limits

## Overview

The Import/Export Service orchestrates data import operations from CSV/Excel files with validation and duplicate detection. It supports both "create" mode (insert new records) and "update" mode (modify existing records by ID), making bulk data operations safe and predictable.

## Architecture

### Domain Model

```
┌─────────────────────────────────────┐
│   ImportExportService               │
├─────────────────────────────────────┤
│   db: AsyncSession                  │
└─────────────────────────────────────┘

Validation Summary:
┌─────────────────────────────────────┐
│   ImportValidationSummary           │
├─────────────────────────────────────┤
│   valid: bool                       │
│   errors: list[dict]                │
│   rows: int                         │
│   warnings: list[str]               │
└─────────────────────────────────────┘

Execution Summary:
┌─────────────────────────────────────┐
│   ImportExecutionSummary            │
├─────────────────────────────────────┤
│   count: int                        │
│   duplicates: int                   │
│   updated: int                      │
│   missing: int                      │
└─────────────────────────────────────┘
```

**Import Modes:**

- `create`: Insert new records, detect duplicates by unique fields
- `update`: Modify existing records by ID, report missing IDs

## API Endpoints

**Base:** `/api/v1/entity/{entity_type}`

| Endpoint           | Method | Description                            |
| ------------------ | ------ | -------------------------------------- |
| `/import/validate` | POST   | Validate import data without executing |
| `/import`          | POST   | Execute validated import               |
| `/export`          | GET    | Export entity data to CSV              |

### Import Request

```json
{
  "mode": "create",
  "headers": ["id", "name", "description", "status"],
  "rows": [
    {
      "id": "ASSET-001",
      "name": "Server Rack A",
      "description": "...",
      "status": "active"
    },
    {
      "id": "ASSET-002",
      "name": "Server Rack B",
      "description": "...",
      "status": "active"
    }
  ]
}
```

### Validation Response

```json
{
  "valid": false,
  "errors": [
    {
      "row": 2,
      "errors": [
        { "field": "id", "message": "Duplicate ID: ASSET-001 already exists" },
        {
          "field": "status",
          "message": "Invalid value 'actve'. Expected: active, inactive"
        }
      ]
    }
  ],
  "rows": 2,
  "warnings": [
    "Update mode requires valid existing record IDs in the import data."
  ]
}
```

### Execution Response

```json
{
  "count": 45,
  "duplicates": 3,
  "updated": 0,
  "missing": 0
}
```

## Core Operations

### Validate Import

```python
async def validate_import(
    meta: EntityMeta,
    headers: list[str],
    rows: list[dict[str, Any]],
    mode: ImportMode = "create",
) -> ImportValidationSummary
```

**Validation Steps:**

1. Header validation (must match entity fields)
2. Required field presence check
3. Data type coercion validation
4. Unique field duplicate detection
5. Link field existence verification
6. Enum value validation

### Execute Import

```python
async def execute_import(
    meta: EntityMeta,
    headers: list[str],
    rows: list[dict[str, Any]],
    mode: ImportMode = "create",
) -> ImportExecutionSummary
```

**Create Mode:**

- Skip rows with duplicate unique keys
- Create valid records
- Report duplicate count

**Update Mode:**

- Find existing record by ID
- Update fields (excluding system fields)
- Report missing IDs
- Report update count

## Frontend Integration

### Import Dialog

**Location:** `frontend/app/components/ImportDialog.vue`

```vue
<UButton @click="showImportDialog = true">
  Import CSV
</UButton>

<UModal v-model="showImportDialog">
  <template #header>Import {{ entityLabel }}</template>
  
  <!-- Step 1: Upload -->
  <UUpload
    accept=".csv,.xlsx"
    @upload="parseFile"
  />
  
  <!-- Step 2: Map Fields -->
  <FieldMapper
    :file-headers="parsedHeaders"
    :entity-fields="entityFields"
    v-model="fieldMapping"
  />
  
  <!-- Step 3: Validate -->
  <UButton @click="validateImport" :loading="validating">
    Validate
  </UButton>
  
  <!-- Step 4: Review Errors -->
  <ErrorTable
    v-if="validationResult?.errors?.length"
    :errors="validationResult.errors"
  />
  
  <!-- Step 5: Execute -->
  <UButton
    @click="executeImport"
    :disabled="!validationResult?.valid"
    color="primary"
  >
    Import {{ validationResult?.rows }} Records
  </UButton>
</UModal>
```

### CSV Parsing

```typescript
// Using PapaParse or similar
import Papa from "papaparse";

function parseCSV(file: File): Promise<{ headers: string[]; rows: any[] }> {
  return new Promise((resolve) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        const headers = results.meta.fields || [];
        resolve({ headers, rows: results.data });
      },
    });
  });
}
```

### Import Store

```typescript
// stores/import.ts
export const useImportStore = defineStore("import", {
  actions: {
    async validateImport(entity: string, data: ImportRequest) {
      return await api.post(`/entity/${entity}/import/validate`, data);
    },

    async executeImport(entity: string, data: ImportRequest) {
      return await api.post(`/entity/${entity}/import`, data);
    },

    async exportData(entity: string, filters?: Record<string, any>) {
      return await api.get(`/entity/${entity}/export`, {
        params: filters,
        responseType: "blob",
      });
    },
  },
});
```

### Export Functionality

```typescript
async function exportToCSV() {
  const blob = await importStore.exportData(entity, listFilters.value);
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${entity}_export_${formatDate(new Date())}.csv`;
  link.click();
  window.URL.revokeObjectURL(url);
}
```

## Entity List Integration

**Location:** `frontend/app/pages/[entity]/index.vue`

```vue
<template #toolbar>
  <UButtonGroup>
    <UButton @click="showImportDialog = true" icon="i-heroicons-arrow-up-tray">
      Import
    </UButton>
    <UButton @click="exportToCSV" icon="i-heroicons-arrow-down-tray">
      Export
    </UButton>
  </UButtonGroup>
</template>
```

## Validation Rules

### Header Validation

```python
header_errors = validate_headers(meta, headers)
# Checks:
# - All required fields present
# - No unknown fields
# - ID field required for update mode
```

### Row Validation

```python
validated_rows, errors = await validate_rows(db, meta, rows, mode=mode)
# Checks per row:
# - Field data types match
# - Required fields have values
# - Link fields reference existing records
# - Unique fields not duplicated
# - Enum values valid
```

### Data Type Coercion

Import uses same coercion as EntityService:

- String → Integer (if valid)
- String → Float (if valid)
- ISO date strings → Date/Datetime
- Empty strings → null (for nullable fields)

## Duplicate Detection

### Create Mode

Detect duplicates by:

1. Primary key (ID) collision
2. Unique field constraints (e.g., email, serial_number)

### Update Mode

Detect missing records:

- ID not found in database
- Reported in `missing` count

## Error Reporting

### Error Format

```json
{
  "row": 5,
  "errors": [
    {
      "field": "email",
      "message": "Invalid email format: 'not-an-email'",
      "value": "not-an-email"
    },
    {
      "field": "department",
      "message": "Link target not found: 'INVALID-DEPT'",
      "value": "INVALID-DEPT"
    }
  ]
}
```

## Testing

**Unit Tests:** `backend/tests/test_import_export.py`

Test scenarios:

- Header validation (valid, missing required, unknown fields)
- Row validation (data types, required fields, links)
- Create mode with duplicates
- Update mode with missing IDs
- CSV parsing and generation
- Error message clarity

## Security

- RBAC: Only users with "create" permission can import
- Row-level validation prevents injection
- File size limits (configurable)
- Allowed file types (.csv, .xlsx)

## Configuration

### Import Limits

```python
# backend/app/core/config.py
MAX_IMPORT_ROWS = 10_000  # Prevent memory issues
MAX_IMPORT_FILE_SIZE_MB = 10
```

### Batch Processing

Large imports processed in batches:

```python
BATCH_SIZE = 100  # Records per batch
```

## Future Enhancements

- Excel (.xlsx) native support
- Import templates (predefined field mappings)
- Scheduled/background imports
- Import history and rollback
- Delta imports (only changed records)
- Relationship import (parent + children)
- Import validation dry-run with detailed report
- Column transformation rules
- Data cleansing hooks

## Maintenance

**Update Triggers**:

- Import/export workflow changes
- New validation rules added
- File processing requirements updated
- Batch processing modifications
- Security requirement changes
- Performance optimization needs

**Verification**:

- Run `pytest tests/test_import_export.py` - all tests must pass
- Test header validation scenarios
- Verify row validation logic
- Test create and update modes
- Check duplicate detection accuracy
- Validate file parsing and generation
- Test error reporting clarity
- Confirm security limits enforcement

**Last Updated**: 2026-04-05
