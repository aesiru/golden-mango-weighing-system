<!-- SCOPE: Application branding configuration and logo management -->
<!-- DOC_KIND: explanation -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Understanding branding system, customizing application appearance, managing logo uploads -->
<!-- SKIP_WHEN: Quick reference - use the Quick Navigation section -->
<!-- PRIMARY_SOURCES: backend/app/application/services/branding_service.py, backend/app/api/routes/branding.py -->

# Branding Service

## Quick Navigation

- [Architecture](#architecture) - Service design and dependencies
- [Core Operations](#core-operations) - Branding management operations
- [Frontend Integration](#frontend-integration) - Usage in application settings
- [Configuration](#configuration) - Branding defaults and customization
- [Testing](#testing) - Test strategies and coverage

## Agent Entry

**Purpose**: The Branding Service manages application branding configuration including organization name, description, and logo upload. It provides a simple interface for customizing the application appearance.

**When to Read**:

- Setting up organization branding
- Customizing application appearance
- Understanding logo upload and management
- Implementing branding in frontend components

**When to Skip**:

- Default application setup
- Static branding configuration
- Simple UI customization needs

**Canonical Status**: This document is the primary source for understanding the Branding Service architecture and configuration.

**Next Steps**: After reading this, explore the frontend branding implementation and logo upload workflows.

**Primary Sources**:

- `backend/app/application/services/branding_service.py` - Core service implementation
- `backend/app/api/routes/branding.py` - Branding API endpoints

## Overview

The Branding Service manages application branding configuration including organization name, description, and logo upload. It provides a simple interface for customizing the application appearance.

## Architecture {#architecture}

### Domain Model

```
┌─────────────────────────────────────┐
│   BrandingService                   │
├─────────────────────────────────────┤
│   store: BrandingStore              │
│   assets_dir: Path                  │
│   uploads_root: Path                │
└─────────────────────────────────────┘

Branding Configuration:
{
  "organization_name": "Acme Corp",
  "description": "A modular application framework",
  "logo_url": "/uploads/branding/logo-a1b2c3d4.png"
}
```

**Default Values:**

- `organization_name`: "My App"
- `description`: "A modular application framework"
- `logo_url`: None

## Core Operations {#core-operations}

### Get Branding

```python
def get_branding() -> dict[str, Any]
```

Returns merged branding configuration (defaults + stored values).

**Example:**

```python
branding = service.get_branding()
# {
#   "organization_name": "Acme Corp",
#   "description": "Custom Instance",
#   "logo_url": "/uploads/branding/logo-a1b2c3d4.png"
# }
```

### Save Branding

```python
def save_branding(
    organization_name: str,
    description: str | None
) -> dict[str, Any]
```

Updates text-based branding configuration.

**Validation:**

- Strips whitespace from inputs
- Preserves existing logo_url

### Save Logo

```python
def save_logo(
    content: bytes,
    original_name: str,
    content_type: str | None
) -> dict[str, Any]
```

**Process:**

1. Determine file extension (from original name or content type)
2. Delete existing logo files
3. Generate unique filename with UUID
4. Write to branding assets directory
5. Update branding configuration with new logo_url

**File Naming:**

- Format: `logo-{uuid8}{extension}`
- Example: `logo-a1b2c3d4.png`

**Supported Formats:**

- PNG, JPG, JPEG, GIF, SVG (via mimetypes)

### Remove Logo

```python
def remove_logo() -> dict[str, Any]
```

Deletes all logo files and clears logo_url from configuration.

## API Endpoints

**Base:** `/api/v1/admin/branding`

| Endpoint | Method | Description                         |
| -------- | ------ | ----------------------------------- |
| `/`      | GET    | Get current branding configuration  |
| `/`      | PUT    | Update branding (name, description) |
| `/logo`  | POST   | Upload logo image                   |
| `/logo`  | DELETE | Remove logo                         |

### Get Branding Response

```json
{
  "organization_name": "Acme Corp",
  "description": "A modular application framework",
  "logo_url": "/uploads/branding/logo-a1b2c3d4.png"
}
```

### Update Branding Request

```json
{
  "organization_name": "Acme Corporation",
  "description": "Global Asset Management Platform"
}
```

### Logo Upload

```bash
curl -X POST http://localhost:8000/api/v1/admin/branding/logo \
  -H "Content-Type: multipart/form-data" \
  -F "file=@logo.png"
```

**Response:**

```json
{
  "organization_name": "Acme Corp",
  "description": "A modular application framework",
  "logo_url": "/uploads/branding/logo-e5f6g7h8.png"
}
```

## Frontend Integration {#frontend-integration}

### Branding Store

```typescript
// stores/branding.ts
export const useBrandingStore = defineStore("branding", {
  state: () => ({
    config: {
      organization_name: "My App",
      description: "Asset Management",
      logo_url: null,
    } as BrandingConfig,
  }),

  actions: {
    async loadBranding() {
      const response = await api.get("/admin/branding");
      this.config = response.data;
    },

    async updateBranding(data: Partial<BrandingConfig>) {
      const response = await api.put("/admin/branding", data);
      this.config = response.data;
    },

    async uploadLogo(file: File) {
      const formData = new FormData();
      formData.append("file", file);

      const response = await api.post("/admin/branding/logo", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      this.config = response.data;
    },

    async removeLogo() {
      const response = await api.delete("/admin/branding/logo");
      this.config = response.data;
    },
  },
});
```

### Branding Settings Page

**Location:** `frontend/app/pages/admin/branding.vue`

```vue
<template>
  <div class="branding-settings">
    <h1>Branding Settings</h1>

    <UForm @submit="saveBranding">
      <UFormGroup label="Organization Name">
        <UInput v-model="form.organization_name" />
      </UFormGroup>

      <UFormGroup label="Description">
        <UInput v-model="form.description" />
      </UFormGroup>

      <UButton type="submit">Save</UButton>
    </UForm>

    <div class="logo-section">
      <h2>Logo</h2>

      <img
        v-if="brandingStore.config.logo_url"
        :src="brandingStore.config.logo_url"
        class="logo-preview"
      />

      <UUpload @upload="handleLogoUpload" accept="image/*" />

      <UButton
        v-if="brandingStore.config.logo_url"
        color="error"
        @click="removeLogo"
      >
        Remove Logo
      </UButton>
    </div>
  </div>
</template>
```

### Application Layout Integration

```vue
<!-- app.vue or layout -->
<template>
  <div class="app">
    <header>
      <img
        v-if="brandingStore.config.logo_url"
        :src="brandingStore.config.logo_url"
        class="app-logo"
      />
      <span class="app-title">{{
        brandingStore.config.organization_name
      }}</span>
    </header>
    ...
  </div>
</template>
```

## Infrastructure Layer

### BrandingStore

**Location:** `backend/app/infrastructure/settings.py`

```python
class BrandingStore:
    """File-based storage for branding configuration."""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.config_file = config_dir / "branding.json"

    def load(self) -> dict:
        if not self.config_file.exists():
            return {}
        return json.loads(self.config_file.read_text())

    def save(self, data: dict) -> dict:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps(data, indent=2))
        return data
```

**Storage Location:**

- Config: `uploads/config/branding.json`
- Assets: `uploads/branding/`

## File Storage

### Directory Structure

```
uploads/
├── config/
│   └── branding.json
├── branding/
│   └── logo-a1b2c3d4.png
└── ...
```

### Logo Cleanup

When uploading new logo, old logos are automatically deleted:

```python
for existing in self.assets_dir.glob("logo.*"):
    existing.unlink(missing_ok=True)
```

## Configuration {#configuration}

**Upload Settings:**

```python
# backend/app/core/config.py
UPLOAD_DIR = Path("uploads")
MAX_UPLOAD_SIZE_MB = 10
```

**File Serving:**

Static files served from `/uploads/` via FastAPI static files:

```python
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
```

## Testing {#testing}

**Unit Tests:** `backend/tests/test_branding_service.py`

Test scenarios:

- Default branding values
- Branding update persistence
- Logo upload with extension detection
- Logo replacement (old file cleanup)
- Logo removal
- Invalid file handling

**Example Test:**

```python
def test_save_logo_generates_unique_filename():
    service = BrandingService(mock_store, assets_dir, uploads_root)

    result = service.save_logo(
        content=b"fake-image-data",
        original_name="old-logo.png",
        content_type="image/png"
    )

    assert result["logo_url"].startswith("/uploads/branding/logo-")
    assert result["logo_url"].endswith(".png")
```

## Security

- Admin-only access to branding endpoints
- File size limits enforced at API layer
- File type validation via mimetypes
- Logo files stored outside web root (served via static files)
- No executable file uploads allowed

## Future Enhancements

- Multiple logo variants (light/dark mode)
- Favicon upload
- Custom color scheme/theming
- Email template branding
- Print/PDF branding
- Logo cropping/resizing
- SVG optimization

## Maintenance

**Update Triggers**:

- Branding configuration changes
- Logo upload process updates
- Storage location changes
- File handling modifications

**Verification**:

- Run `pytest tests/test_branding_service.py` - all tests must pass
- Test default branding values
- Verify branding update persistence
- Check logo upload with various formats
- Test logo replacement cleanup
- Validate logo removal
- Confirm file serving works correctly

**Last Updated**: 2026-04-05
