<!-- SCOPE: Application service documentation for workflow state management orchestration -->
<!-- DOC_KIND: reference -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Understanding workflow architecture, implementing state transitions, configuring workflow definitions -->
<!-- SKIP_WHEN: Quick API reference - use the Quick Navigation section -->
<!-- PRIMARY_SOURCES: backend/app/application/services/workflow_service.py, backend/app/api/routes/entity_workflow.py, backend/app/models/workflow.py -->

# Workflow Service

## Quick Navigation

- [Architecture](#architecture) - Service design and dependencies
- [Workflow Metadata Structure](#workflow-metadata-structure) - State and action definitions
- [API Endpoints](#api-endpoints) - Workflow REST API specifications
- [Core Operations](#core-operations) - State management and transitions
- [Frontend Integration](#frontend-integration) - UI components and state display
- [Database Schema](#database-schema) - Workflow tables and relationships
- [Configuration](#configuration) - Entity workflow enablement
- [Integration Points](#integration-points) - Entity service and hook integration
- [Testing](#testing) - Test strategies and coverage
- [Error Handling](#error-handling) - Common error scenarios and resolutions

## Agent Entry

**Purpose**: The Workflow Service orchestrates workflow transitions for entities with workflow-enabled metadata. It provides workflow metadata retrieval, state management, and transition validation while delegating database operations to WorkflowRepository.

**When to Read**:

- Implementing workflow state transitions
- Configuring workflow definitions
- Understanding workflow metadata structure
- Troubleshooting transition validation
- Building workflow UI components

**When to Skip**: Quick workflow API reference - use the Quick Navigation section above

**Canonical**: This is the primary reference for workflow service architecture and state management patterns

**Next**: Read Architecture section to understand service design, then Workflow Metadata Structure for data models

**Primary Sources**:

- `backend/app/application/services/workflow_service.py` - Core service implementation
- `backend/app/api/routes/entity_workflow.py` - Workflow API endpoints
- `backend/app/models/workflow.py` - Database schema definitions

## Overview

The Workflow Service orchestrates workflow transitions for entities with workflow-enabled metadata. It provides workflow metadata retrieval, state management, and transition validation while delegating database operations to the WorkflowRepository.

## Architecture

### Domain Model

```
┌─────────────────────────────────────┐
│   WorkflowAppService                │
├─────────────────────────────────────┤
│   workflow_repo: WorkflowRepository │
│   entity_repo: EntityRepository     │
└─────────────────────────────────────┘
```

**Key Responsibilities:**

- Workflow metadata retrieval for frontend visualization
- Initial state determination for new records
- Available actions based on current state
- Transition validation (can user perform action from current state?)

## Workflow Metadata Structure

### State Definition

```json
{
  "slug": "pending_approval",
  "label": "Pending Approval",
  "color": "#f59e0b",
  "is_initial": false,
  "actions": [
    {
      "slug": "approve",
      "label": "Approve",
      "target_slug": "approved",
      "target_label": "Approved"
    }
  ]
}
```

### Workflow Response Format

```json
{
  "enabled": true,
  "initial_state": "draft",
  "states": {
    "draft": { ... },
    "pending_approval": { ... },
    "approved": { ... }
  }
}
```

## API Endpoints

**Base:** `/api/v1/entity/{entity_type}/{record_id}`

| Endpoint               | Method | Description                             |
| ---------------------- | ------ | --------------------------------------- |
| `/workflow`            | GET    | Get workflow metadata for entity type   |
| `/workflow/actions`    | GET    | Get available actions for current state |
| `/workflow/transition` | POST   | Execute workflow action transition      |

### Transition Request

```json
{
  "action": "submit_for_approval",
  "current_state": "draft"
}
```

### Transition Response

```json
{
  "success": true,
  "target_state": "pending_approval",
  "previous_state": "draft"
}
```

## Core Operations

### Get Workflow Metadata

Builds comprehensive workflow definition including:

- All states with colors and labels
- Available actions per state
- Initial state identification
- State linkage relationships

### Validate and Transition

```python
async def validate_and_transition(
    entity: str,
    record_id: str,
    action: str,
    current_state: str,
    user: Any = None,
) -> tuple[bool, Optional[str], Optional[str]]
```

**Returns:** `(is_valid, target_state_or_none, error_message_or_none)`

**Validation Rules:**

1. Action must exist for current state
2. User must have workflow transition permission
3. Target state must be valid
4. Transition must not violate business rules

## Frontend Integration

### Workflow State Display

**Component:** `WorkflowStateBadge.vue`

```vue
<UBadge :color="stateColor" :label="stateLabel" size="md" />
```

### Workflow Actions Dropdown

**Component:** `WorkflowActions.vue`

```typescript
const actions = await entityApi.getWorkflowActions(entity, recordId);

// Available actions based on current state
actions.forEach((action) => {
  console.log(action.slug); // "submit_for_approval"
  console.log(action.label); // "Submit for Approval"
  console.log(action.target_state); // "pending_approval"
});
```

### Transition Execution

```typescript
async function executeTransition(action: string) {
  try {
    const result = await entityApi.workflowTransition(
      entity,
      recordId,
      action,
      currentState,
    );

    if (result.success) {
      toast.add({
        title: `Moved to ${result.target_state}`,
        color: "success",
      });
      await loadData(); // Refresh record
    }
  } catch (error) {
    toast.add({
      title: error.message,
      color: "error",
    });
  }
}
```

### Entity Detail Integration

**Location:** `frontend/app/pages/[entity]/[id]/index.vue`

Workflow state displayed in:

- Record header (badge)
- Actions dropdown (workflow transitions)
- History tab (state changes)

## Database Schema

### workflow_state

- `id`: Primary key
- `slug`: Unique state identifier
- `label`: Display name
- `color`: Hex color code for UI

### workflow_action

- `id`: Primary key
- `slug`: Unique action identifier
- `label`: Display name

### workflow_state_link

- Links states to workflows with `is_initial` flag
- `sort_order` for display sequence

### workflow_transition

- `from_state_id` → `to_state_id`
- `action_ref_id`: Required action
- Guards/conditions for conditional transitions

## Configuration

### Entity Workflow Enablement

**Entity JSON:**

```json
{
  "workflow": {
    "enabled": true,
    "initial_state": "draft",
    "state_field": "workflow_state",
    "states": ["draft", "pending_approval", "approved", "rejected"]
  }
}
```

### Workflow States (Database-Driven)

States managed via admin UI or seeders:

- `backend/app/models/workflow.py`
- Admin routes: `/api/admin/workflow/states`
- Admin routes: `/api/admin/workflow/transitions`

## Integration Points

### Entity Service Integration

Workflow state auto-set on create:

```python
# In EntityService.create()
if meta.workflow and meta.workflow.enabled and not data.get("workflow_state"):
    data["workflow_state"] = meta.workflow.initial_state
```

### Hook System

Workflow transitions trigger hooks:

- `before_workflow_transition`
- `after_workflow_transition`

## Testing

**Unit Tests:** `backend/tests/test_workflow_service.py`

Test scenarios:

- Workflow metadata retrieval
- Available actions filtering
- Valid transition execution
- Invalid transition rejection
- Initial state assignment
- State color resolution

## Security

- Workflow transitions respect RBAC permissions
- Guards can enforce business rules (e.g., "cannot approve own request")
- Audit logging for all state changes

## Error Handling

| Error                   | Cause                    | Resolution               |
| ----------------------- | ------------------------ | ------------------------ |
| `WorkflowError`         | Invalid transition       | Check available actions  |
| `PermissionDeniedError` | No transition permission | Request appropriate role |
| `EntityNotFoundError`   | Record doesn't exist     | Verify record ID         |

## Future Enhancements

- Conditional transitions with expression evaluation
- Parallel workflow branches
- Time-based auto-transitions
- Workflow diagrams (visual designer)
- Workflow versioning

## Maintenance

**Update Triggers**:

- Workflow definition changes
- New transition types added
- State modification requirements
- Guard rule updates
- Integration point changes
- Security requirement updates

**Verification**:

- Run `pytest tests/test_workflow_service.py` - all tests must pass
- Test workflow metadata retrieval for all entities
- Verify available actions filtering
- Test valid and invalid transition execution
- Check initial state assignment
- Validate state color resolution
- Confirm hook execution for transitions

**Last Updated**: 2026-04-05
