# Frontend — FastAPI Nuxt Starter

A metadata-driven frontend built with **Nuxt 4** and **Nuxt UI** for the FastAPI modular backend.

## Tech Stack

- **Framework**: Nuxt 4
- **UI Library**: Nuxt UI
- **Styling**: Tailwind CSS
- **TypeScript**: Full TypeScript support
- **State Management**: Pinia
- **API Client**: Custom `$fetch` wrapper with JWT authentication

## Features

- Dynamic entity management — list/detail forms auto-generated from metadata
- JWT-based authentication with automatic token refresh
- Workflow management UI (state transitions, progress trees)
- User and role administration
- Branding settings (organization name, logo, theme)
- Import/Export interface
- Model editor (Frappe-like data model designer)
- Notification inbox with real-time updates
- Role-based dashboards

## Getting Started

```bash
pnpm install
pnpm dev
```

### Environment

Create a `.env` file:

```bash
NODE_ENV=development
NUXT_PUBLIC_API_URL=http://127.0.0.1:8012/api
NUXT_PUBLIC_WS_URL=ws://127.0.0.1:8012
```

## Project Structure

```
frontend/
├── app/
│   ├── components/       # Vue components (entity, workflow, admin, etc.)
│   ├── composables/      # Reusable composition functions (API wrappers)
│   ├── layouts/          # Layout components (default, login)
│   ├── middleware/        # Route middleware (auth)
│   ├── pages/            # File-based routing
│   │   ├── [entity]/     # Dynamic entity list/detail pages
│   │   ├── admin/        # Admin panel (users, roles, permissions)
│   │   ├── model-editor/ # Data model editor
│   │   ├── profile/      # User profile
│   │   ├── workflow/     # Workflow management
│   │   └── ...
│   ├── plugins/          # Nuxt plugins (auth, socket.io)
│   ├── stores/           # Pinia stores (auth, cache, modals)
│   └── types/            # TypeScript type definitions
├── e2e/                  # Playwright E2E tests
├── tests/                # Vitest unit tests
└── nuxt.config.ts
```

## Key Composables

| Composable | Purpose |
|---|---|
| `useApi()` | Generic API methods (meta, entity CRUD, login) |
| `useAuth()` | Authentication state management |
| `useEntityApi()` | Entity-specific CRUD operations |
| `useEntityWorkflow()` | Workflow action dispatch |
| `useBootInfo()` | Application boot configuration |
| `useBrandingSettings()` | Organization branding CRUD |
| `useDashboard()` | Role-based dashboard widgets |
| `useNotificationCenter()` | Notification inbox management |

## Dynamic Entity Pages

The `[entity]/index.vue` and `[entity]/[id].vue` pages render any registered entity:

- **List view** — paginated table with filters, sort, and search
- **Detail view** — metadata-driven form with fields rendered by type
- **Child tables** — inline grid editing for child entities
- **Workflow** — state transition buttons and progress timeline
- **Attachments** — file upload/download per record

No per-entity page code is needed.

## Build for Production

```bash
pnpm build
node .output/server/index.mjs
```
