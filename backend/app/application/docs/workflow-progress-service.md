<!-- SCOPE: Application service documentation for hierarchical workflow progress visualization -->
<!-- DOC_KIND: reference -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Understanding workflow progress architecture, implementing progress trees, managing child node visualization -->
<!-- SKIP_WHEN: Quick API reference - use the Quick Navigation section -->
<!-- PRIMARY_SOURCES: backend/app/application/services/workflow_progress_service.py, backend/app/api/routes/entity_workflow.py, backend/app/models/workflow.py -->

# Workflow Progress Service

## Quick Navigation

- [Architecture](#architecture) - Service design and domain model
- [API Endpoints](#api-endpoints) - Progress REST API specifications
- [Core Operations](#core-operations) - Recursive node building
- [Entity-Specific Builders](#entity-specific-builders) - Purchase request, maintenance, asset, WOA patterns
- [Frontend Integration](#frontend-integration) - Progress component and stepper visualization
- [Workflow Definition Sources](#workflow-definition-sources) - Database-driven vs metadata
- [State Normalization](#state-normalization) - Consistent state formatting
- [Transition Descriptions](#transition-descriptions) - Human-readable guidance
- [Configuration](#configuration) - Title field and hidden states
- [Testing](#testing) - Test strategies and coverage
- [Performance](#performance) - Optimization and loading strategies

## Agent Entry

**Purpose**: The Workflow Progress Service builds hierarchical workflow progress trees for entity records. It creates visual workflow steppers with child node relationships, enabling users to understand record progress through complex business processes like Purchase Requests, Maintenance Requests, and Work Orders.

**When to Read**:

- Understanding workflow progress visualization
- Implementing progress tree building
- Managing entity-specific child builders
- Building workflow stepper components
- Understanding state normalization and transitions
- Configuring workflow definition sources

**When to Skip**: Quick progress API reference - use the Quick Navigation section above

**Canonical**: This is the primary reference for workflow progress service architecture and hierarchical visualization

**Next**: Read Architecture section to understand service design, then Core Operations for recursive building

**Primary Sources**:

- `backend/app/application/services/workflow_progress_service.py` - Core service implementation
- `backend/app/api/routes/entity_workflow.py` - Progress API endpoints
- `backend/app/models/workflow.py` - Database schema definitions

## Overview

The Workflow Progress Service builds hierarchical workflow progress trees for entity records. It creates visual workflow steppers with child node relationships, enabling users to understand record progress through complex business processes like Purchase Requests, Maintenance Requests, and Work Orders.

## Architecture

### Domain Model

```
┌─────────────────────────────────────┐
│   WorkflowProgressService           │
├─────────────────────────────────────┤
│   workflow_repo: WorkflowRepository │
│   entity_repo: EntityRepository     │
└─────────────────────────────────────┘

Progress Node Structure:
{
  "entity": "purchase_request",
  "record_id": "PR-001",
  "label": "Purchase Request",
  "title": "Office Supplies Q2",
  "current_state": "pending_approval",
  "current_state_label": "Pending Approval",
  "next_actions": [...],
  "steps": [...],
  "summary": "2 of 3 lines received",
  "children": [...]
}
```

**Entity-Specific Builders:**

- `purchase_request` → Builds purchase request lines as children
- `maintenance_request` → Links work order activity and work order
- `asset` → Shows maintenance requests and installation positions
- `work_order_activity` → Displays item issues and returns

## API Endpoints

**Base:** `/api/v1/entity/{entity_type}/{record_id}`

| Endpoint    | Method | Description                              |
| ----------- | ------ | ---------------------------------------- |
| `/progress` | GET    | Get workflow progress tree with children |

### Response Format

```json
{
  "entity": "purchase_request",
  "record_id": "PR-001",
  "title": "Office Supplies Q2",
  "summary": "2 of 3 lines are fully received",
  "node": {
    "entity": "purchase_request",
    "record_id": "PR-001",
    "label": "Purchase Request",
    "title": "Office Supplies Q2",
    "current_state": "pending_approval",
    "current_state_label": "Pending Approval",
    "next_actions": [
      {
        "action": "approve",
        "label": "Approve",
        "target_state": "approved",
        "target_label": "Approved",
        "description": "Approve the request so downstream procurement can begin."
      }
    ],
    "steps": [
      {
        "key": "draft",
        "title": "Draft",
        "description": "Completed step: Draft.",
        "status": "completed",
        "current": false
      },
      {
        "key": "pending_approval",
        "title": "Pending Approval",
        "description": "Current step. Next: Approve → Approved.",
        "status": "current",
        "current": true
      }
    ],
    "summary": "2 of 3 lines are fully received",
    "children": [...]
  }
}
```

## Core Operations

### Build Node (Recursive)

```python
async def _build_node(entity: str, record: Any) -> dict[str, Any]
```

**Process:**

1. Load workflow definition (DB or entity metadata)
2. Extract record title using `title_field`
3. Determine current state (normalized)
4. Build available next actions
5. Build step-by-step progress visualization
6. Build entity-specific children
7. Generate summary

### Entity-Specific Child Builders

**Purchase Request Children:**

```python
async def _build_purchase_request_children(purchase_request_id: str)
```

- Fetches all purchase request lines
- Builds progress node for each line
- Calculates received quantities
- Determines if parent is "closable"
- Summary: "{X} of {Y} lines fully received"

**Maintenance Request Children:**

```python
async def _build_maintenance_request_children(record: Any)
```

- Links work order activity (if exists)
- Links work order (via activity)
- Shows current state of each linked record

**Asset Children:**

```python
async def _build_asset_children(asset_id: str)
```

- Shows active maintenance requests
- Shows current installation position
- Prioritizes open maintenance requests

**Work Order Activity Children:**

```python
async def _build_work_order_activity_children(work_order_activity_id: str)
```

- Lists linked item issues
- Lists linked item returns
- Shows completion status

### Build Steps

Creates visual stepper with statuses:

- `completed`: Steps before current
- `current`: Active step with next actions
- `upcoming`: Future steps with transition descriptions

**Step Description Logic:**

- Current step: Shows next possible actions
- Completed: Simple completion message
- Upcoming: Shows required transition

## Frontend Integration

### Workflow Progress Component

**Location:** `frontend/app/components/WorkflowProgress.vue`

```vue
<WorkflowProgress
  :entity="entity"
  :record-id="recordId"
  :node="progressNode"
  @transition="executeTransition"
/>
```

### Steps Visualization

**Component:** `UStepper` or custom vertical stepper

```typescript
// Steps are pre-sorted by workflow definition
const steps = progressNode.steps;

// Current step index
const currentIndex = steps.findIndex((s) => s.current);
```

### Next Actions Panel

```vue
<div class="next-actions">
  <h4>Available Actions</h4>
  <UButton
    v-for="action in progressNode.next_actions"
    :key="action.action"
    @click="executeTransition(action.action)"
  >
    {{ action.label }}
  </UButton>
</div>
```

### Children Tree

Recursive tree display:

```vue
<WorkflowNode
  v-for="child in progressNode.children"
  :key="child.record_id"
  :node="child"
  :depth="depth + 1"
/>
```

### Entity Detail Tab

**Location:** `frontend/app/pages/[entity]/[id].vue` - "Progress" tab

```typescript
const { data: progress } = await useAsyncData("progress", () =>
  entityApi.getWorkflowProgress(entity, id),
);
```

## Workflow Definition Sources

### Database-Driven (Primary)

Tables: `workflow_state`, `workflow_action`, `workflow_transition`, `workflow_state_link`

**Advantages:**

- Runtime modifiable
- Multiple workflows per entity type
- Rich transition conditions

### Entity Metadata (Fallback)

```json
{
  "workflow": {
    "states": [
      { "slug": "draft", "label": "Draft" },
      { "slug": "approved", "label": "Approved" }
    ],
    "transitions": [{ "from": "draft", "to": "approved", "action": "approve" }]
  }
}
```

## State Normalization

All states normalized to lowercase with underscores:

```python
_normalize_state("Pending Approval")  # → "pending_approval"
_normalize_state("In Progress")       # → "in_progress"
```

## Transition Descriptions

Human-readable descriptions for each entity-action combination:

```python
guide = {
    "purchase_request": {
        "submit_for_review": "Move the request into review...",
        "approve": "Approve the request so downstream...",
    },
    "work_order": {
        "start": "Start the work order after linked activities...",
        "complete": "Close the work order after...",
    }
}
```

## Configuration

### Title Field Resolution

```python
def _get_record_title(entity: str, record: Any) -> str:
    meta = MetaRegistry.get(entity)
    if meta and getattr(meta, "title_field", None):
        value = getattr(record, meta.title_field, None)
        if value:
            return str(value)
    return str(record.id or entity)
```

### Hidden Terminal States

States hidden from stepper (but still valid):

```python
hidden_terminal_states = {"rejected"}
```

## Testing

**Unit Tests:** `backend/tests/test_workflow_progress.py`

Test scenarios:

- Progress tree building for each entity type
- Child node recursion
- Step status calculation
- State normalization
- Title field resolution
- Summary generation

## Performance

- Recursive queries for child nodes
- N+1 minimized with batch loading
- Cache frequently accessed workflow definitions
- Lazy loading for deep trees

## Future Enhancements

- Workflow diagrams (graph visualization)
- Time-based progress tracking
- Critical path analysis
- Predicted completion dates
- Workflow bottlenecks identification
- Step duration analytics

## Maintenance

**Update Triggers**:

- Progress tree building changes
- New entity-specific builders added
- State normalization updates
- Transition description modifications
- Workflow definition source changes
- Child node relationship updates

**Verification**:

- Run `pytest tests/test_workflow_progress.py` - all tests must pass
- Test progress tree building for all entity types
- Verify child node recursion accuracy
- Check step status calculation
- Validate state normalization
- Test title field resolution
- Confirm summary generation logic
- Check performance optimization effectiveness

**Last Updated**: 2026-04-05
