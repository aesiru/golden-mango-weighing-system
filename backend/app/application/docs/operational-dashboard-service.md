<!-- SCOPE: Aggregated operational data for dashboard with role-based access -->
<!-- DOC_KIND: explanation -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Understanding dashboard service, role-based access patterns, operational data aggregation -->
<!-- SKIP_WHEN: Quick reference - use Quick Navigation section -->
<!-- PRIMARY_SOURCES: backend/app/application/services/operational_dashboard_service.py, backend/app/api/routes/operational_dashboard.py -->

# Operational Dashboard Service

## Overview

<!-- Provide a brief summary of the service and its purpose -->

## Quick Navigation

- [Architecture](#architecture) - Service design and domain model
- [Core Operations](#core-operations) - Dashboard data aggregation methods
- [Role-Based Access](#role-based-access) - Access control implementation
- [Frontend Integration](#frontend-integration) - Dashboard component usage
- [Testing](#testing) - Test strategies and coverage

## Agent Entry

**Purpose**: The Operational Dashboard Service provides aggregated operational data for dashboard visualization with role-based access control. It delivers work order summaries, status breakdowns, and recent activity with display name resolution.

**When to Read**:

- Understanding dashboard data aggregation patterns
- Implementing role-based access control
- Creating dashboard visualizations
- Integrating with display name resolution

**When to Skip**:

- Simple entity listing without aggregation
- Basic CRUD operations without dashboard logic
- Direct database queries without role filtering

**Canonical Status**: This document is the primary source for understanding the Operational Dashboard Service architecture and data aggregation patterns.

**Next Steps**: After reading this, explore frontend dashboard implementation and role-based access patterns.

**Primary Sources**:

- `backend/app/application/services/operational_dashboard_service.py` - Core service implementation
- `backend/app/api/routes/operational_dashboard.py` - Dashboard API endpoints

## Overview

The Operational Dashboard Service provides aggregated operational data for dashboard visualization with role-based access control. It delivers work order summaries, status breakdowns, and recent activity with display name resolution.

## Architecture {#architecture}

### Domain Model

```
┌─────────────────────────────────────┐
│   OperationalDashboardService       │
├─────────────────────────────────────┤
│   db: AsyncSession                  │
│   _repo: EntityRepository           │
│   _display_name_service: DisplayNameService │
│   current_user: CurrentUser         │
└─────────────────────────────────────┘
```

**Role-Based Access:**

- Superusers: Full access
- Admin role: Full access
- Manager role: Full access
- Operations role: Dashboard access
- Others: 403 Forbidden

## Core Operations {#core-operations}

### Get Work Order Summary

```python
async def get_work_order_summary() -> Dict[str, Any]
```

**Returns:**

```json
{
  "summary": {
    "total": 150,
    "by_status": {
      "draft": 10,
      "in_progress": 45,
      "on_hold": 5,
      "completed": 80,
      "closed": 10
    },
    "overdue": 12
  },
  "activity_summary": {
    "in_progress": {
      "started": 30,
      "pending": 15
    },
    "completed": {
      "finished": 80
    }
  },
  "recent": [
    {
      "id": "WO-001",
      "display_name": "Fix HVAC Unit - Building A",
      "status": "in_progress",
      "updated_at": "2026-04-05T10:30:00Z"
    }
  ]
}
```

**Data Sources:**

- Status counts from `work_order` table
- Overdue count (due_date < today, not closed)
- Activity summary from work_order + work_order_activity join
- Recent 5 records with display name resolution

### Get Maintenance Request Summary

```python
async def get_maintenance_request_summary() -> Dict[str, Any]
```

Returns maintenance request metrics by status and priority.

### Get Asset Overview

```python
async def get_asset_overview() -> Dict[str, Any]
```

Returns asset counts by:

- Status (active, inactive, retired)
- Asset class
- Location
- Criticality

### Get Pending Approvals

```python
async def get_pending_approvals() -> List[Dict[str, Any]]
```

Returns records requiring user action/approval.

## API Endpoints

**Base:** `/api/v1/dashboard`

| Endpoint                   | Method | Description                | Access                     |
| -------------------------- | ------ | -------------------------- | -------------------------- |
| `/operational`             | GET    | Full operational dashboard | operations, admin, manager |
| `/operational/work-orders` | GET    | Work order summary         | operations, admin, manager |
| `/operational/maintenance` | GET    | Maintenance summary        | operations, admin, manager |
| `/operational/assets`      | GET    | Asset overview             | operations, admin, manager |
| `/operational/pending`     | GET    | Pending approvals          | authenticated              |

### Response Format

```json
{
  "work_orders": {
    "summary": { ... },
    "activity_summary": { ... },
    "recent": [ ... ]
  },
  "maintenance_requests": {
    "summary": { ... },
    "by_priority": { ... }
  },
  "assets": {
    "total": 500,
    "by_status": { ... },
    "by_class": { ... }
  },
  "pending_approvals": [
    {
      "entity": "purchase_request",
      "id": "PR-001",
      "display_name": "Office Supplies Q2",
      "action_required": "approve",
      "created_at": "2026-04-04T15:30:00Z"
    }
  ]
}
```

## SQL Queries

### Status Count

```sql
SELECT workflow_state, COUNT(*) as count
FROM work_order
GROUP BY workflow_state
```

### Overdue Count

```sql
SELECT COUNT(*) as count
FROM work_order
WHERE due_date < CURRENT_DATE
  AND workflow_state != 'Closed'
```

### Activity Summary

```sql
SELECT
    w.workflow_state,
    a.workflow_state as activity_state,
    COUNT(*) as count
FROM work_order w
LEFT JOIN work_order_activity a ON w.id = a.work_order
WHERE w.workflow_state != 'Closed'
GROUP BY w.workflow_state, a.workflow_state
```

### Recent Records

```sql
SELECT id, workflow_state, description, updated_at
FROM work_order
ORDER BY updated_at DESC
LIMIT 5
```

## Frontend Integration {#frontend-integration}

### Dashboard Store

```typescript
// stores/dashboard.ts
export const useDashboardStore = defineStore("dashboard", {
  state: () => ({
    data: null as DashboardData | null,
    loading: false,
  }),

  actions: {
    async loadDashboard() {
      this.loading = true;
      try {
        const response = await api.get("/dashboard/operational");
        this.data = response.data;
      } finally {
        this.loading = false;
      }
    },
  },

  getters: {
    workOrderStats: (state) => state.data?.work_orders?.summary,
    overdueCount: (state) => state.data?.work_orders?.summary?.overdue,
    recentWorkOrders: (state) => state.data?.work_orders?.recent,
    pendingApprovals: (state) => state.data?.pending_approvals,
  },
});
```

### Dashboard Page

**Location:** `frontend/app/pages/dashboard/index.vue`

```vue
<template>
  <div class="dashboard">
    <!-- Stats Cards -->
    <div class="stats-grid">
      <UCard>
        <template #header>Total Work Orders</template>
        <div class="stat-value">{{ dashboardStore.workOrderStats?.total }}</div>
      </UCard>

      <UCard>
        <template #header>Overdue</template>
        <div class="stat-value text-red-600">
          {{ dashboardStore.workOrderStats?.overdue }}
        </div>
      </UCard>

      <UCard>
        <template #header>Pending Approvals</template>
        <div class="stat-value">
          {{ dashboardStore.pendingApprovals?.length }}
        </div>
      </UCard>
    </div>

    <!-- Status Breakdown -->
    <UCard title="Work Order Status">
      <div class="status-bars">
        <div
          v-for="(count, status) in dashboardStore.workOrderStats?.by_status"
          :key="status"
          class="status-bar"
        >
          <span class="status-label">{{ status }}</span>
          <UProgress
            :value="count"
            :max="dashboardStore.workOrderStats?.total"
          />
          <span class="status-count">{{ count }}</span>
        </div>
      </div>
    </UCard>

    <!-- Recent Activity -->
    <UCard title="Recent Work Orders">
      <UTable :data="dashboardStore.recentWorkOrders" />
    </UCard>
  </div>
</template>
```

## Display Name Resolution

All records include resolved display names for better readability:

```python
# In get_work_order_summary()
for row in recent_rows:
    record = {
        'id': row.id,
        'workflow_state': row.workflow_state,
        'description': row.description,
    }
    display_name = await self._display_name_service.resolve(
        'work_order',
        record
    )
    recent.append({
        'id': row.id,
        'display_name': display_name,
        'status': row.workflow_state,
    })
```

## Security

### Role Checking

```python
def _has_role(self, required_role: str) -> bool:
    if not self.current_user:
        return False

    # Superusers bypass all checks
    if self.current_user.is_superuser:
        return True

    user_roles = self.current_user.roles or []
    return (
        required_role in user_roles or
        'admin' in user_roles or
        'manager' in user_roles
    )
```

### HTTP 403 Response

```python
if not self._has_role('operations'):
    raise HTTPException(
        status_code=403,
        detail="Access denied"
    )
```

## Performance

- Single query per metric (no N+1)
- Display name resolution batched
- LIMIT 5 for recent records
- Database indexes on workflow_state, due_date
- Async SQLAlchemy for non-blocking queries

## Database Indexes

Recommended indexes for dashboard queries:

```sql
CREATE INDEX idx_work_order_state ON work_order(workflow_state);
CREATE INDEX idx_work_order_due_date ON work_order(due_date);
CREATE INDEX idx_work_order_updated ON work_order(updated_at DESC);
```

## Testing {#testing}

**Unit Tests:** `backend/tests/test_operational_dashboard.py`

Test scenarios:

- Work order summary aggregation
- Overdue calculation accuracy
- Activity summary joins
- Display name resolution
- Role-based access control
- Empty data handling

**Example Test:**

```python
async def test_work_order_summary_requires_operations_role():
    # User without operations role
    user = CurrentUser(roles=['user'])
    service = OperationalDashboardService(db, user)

    with pytest.raises(HTTPException) as exc:
        await service.get_work_order_summary()

    assert exc.value.status_code == 403
```

## Future Enhancements

- Real-time dashboard updates (WebSocket)
- Custom date range filtering
- Comparative analytics (week over week)
- Chart/graph data endpoints
- Export to PDF/Excel
- Personalized dashboard layout
- Key performance indicators (KPIs)
- Predictive maintenance metrics
- Cost analysis dashboard
- Resource utilization charts

## Maintenance

**Update Triggers**:

- Dashboard metric changes
- New aggregation requirements
- Role access modifications
- SQL query optimization

**Verification**:

- Run `pytest tests/test_operational_dashboard.py` - all tests must pass
- Test work order summary accuracy
- Verify overdue calculation
- Check activity summary joins
- Test display name resolution
- Validate role-based access
- Confirm performance with large datasets

**Last Updated**: 2026-04-05
