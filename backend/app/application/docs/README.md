# Application Layer Documentation

## Architecture Decision Records

| ADR | Title | Description |
|---|---|---|
| [ADR-001](adr-001-core-framework-separation.md) | Core Framework Entity Separation | Rationale for consolidating core entities into `app/core/framework/` |

## Features

| Feature | Description | File |
|---|---|---|
| **Entity Service** | Generic CRUD operations for all entities with metadata-driven architecture | [entity-service.md](entity-service.md) |
| **Auth Service** | Authentication orchestration with JWT tokens and password management | [auth-service.md](auth-service.md) |
| **RBAC Service** | Role-based access control with permission caching | [rbac-service.md](rbac-service.md) |
| **Workflow Service** | Workflow state management and transition orchestration | [workflow-service.md](workflow-service.md) |
| **Workflow Progress Service** | Hierarchical workflow progress trees with child node visualization | [workflow-progress-service.md](workflow-progress-service.md) |
| **Metadata Sync Service** | Frappe-inspired atomic metadata sync with model generation and migrations | [metadata-sync-service.md](metadata-sync-service.md) |
| **Import/Export Service** | CSV/Excel import with validation and duplicate detection | [import-export-service.md](import-export-service.md) |
| **Display Name Service** | Dynamic display name resolution with linked record title lookup | [display-name-service.md](display-name-service.md) |
| **Tree Service** | Hierarchical data management for tree-configured entities | [tree-service.md](tree-service.md) |
| **Fetch From Service** | Partial field fetching with resolved link titles | [fetch-from-service.md](fetch-from-service.md) |
| **Hooks System** | Decorator-based entity lifecycle hook registry | [hooks-system.md](hooks-system.md) |
| **Branding Service** | Organization branding configuration and logo management | [branding-service.md](branding-service.md) |
| **Operational Dashboard Service** | Role-based dashboard data aggregation | [operational-dashboard-service.md](operational-dashboard-service.md) |
| **Base Entity API** | Foundation class for per-entity API layers with lifecycle hooks | [base-entity-api.md](base-entity-api.md) |
| **Email Notifications** | Subscription-based email alerts for entity lifecycle events and workflow state changes | [email-notifications.md](email-notifications.md) |

## Architecture Overview

The Application layer orchestrates domain operations and coordinates between the Domain and Infrastructure layers. Each feature documented here represents a cohesive business capability with defined APIs, data models, and integration points.

## Documentation Standards

Each feature document MUST include:

- Domain model with field definitions
- API endpoint specifications
- Frontend component mappings
- Integration points and triggers
- State management patterns
- Testing approach

## Quick Reference

### Common Patterns

- **Data Tables**: UTable + TanStack Table with custom cell templates
- **Loading States**: Skeleton rows with carousel animation
- **State Management**: Pinia stores with computed properties
- **API Integration**: REST endpoints with async/await patterns
- **Error Handling**: Toast notifications with color-coded severity

### Core Framework Quick Reference

| Import Path | Entities Available |
|---|---|
| `from app.core.framework import User, Role` | Authentication entities |
| `from app.core.framework import WorkflowState, Workflow` | Workflow engine |
| `from app.core.framework import ErrorLog, AuditLog, Attachment` | Infrastructure logging |
| `from app.core.framework import ModuleOrder, EntityOrder` | Display ordering |

See [MODULE_DEVELOPER_GUIDE.md](../../core/framework/MODULE_DEVELOPER_GUIDE.md) for complete API reference.
