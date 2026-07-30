<!-- SCOPE: Application service documentation for subscription-based email notifications -->
<!-- DOC_KIND: reference -->
<!-- DOC_ROLE: canonical -->
<!-- READ_WHEN: Understanding notification architecture, implementing email alerts, managing subscriptions -->
<!-- SKIP_WHEN: Quick API reference - use the Quick Navigation section -->
<!-- PRIMARY_SOURCES: backend/app/application/email_notifications/, backend/app/api/routes/email_notifications.py, backend/app/application/services/email_notification_service.py -->

# Email Notifications System

## Quick Navigation

- [Backend Components](#backend-components) - Catalog and service architecture
- [API Endpoints](#api-endpoints) - Notification REST API specifications
- [Frontend Components](#frontend-components) - Data table and subscription UI
- [User Flow](#user-flow) - End-to-end user experience
- [Integration Points](#integration-points) - Entity lifecycle and scheduler triggers
- [Configuration](#configuration) - No special configuration required
- [Testing](#testing) - Test strategies and coverage
- [Future Enhancements](#future-enhancements) - Potential improvements
- [References](#references) - External documentation links

## Agent Entry

**Purpose**: The Email Notifications System provides a subscription-based notification service that allows users to opt into email alerts for various entity lifecycle events and workflow state changes.

**When to Read**:

- Understanding notification architecture
- Implementing subscription management
- Configuring notification catalog
- Building notification UI components
- Troubleshooting email delivery issues
- Managing entity lifecycle notifications

**When to Skip**: Quick notification API reference - use the Quick Navigation section above

**Canonical**: This is the primary reference for email notification system architecture and integration patterns

**Next**: Read Backend Components to understand catalog structure, then API Endpoints for integration details

**Primary Sources**:

- `backend/app/application/email_notifications/` - Catalog and dispatcher
- `backend/app/api/routes/email_notifications.py` - Notification API endpoints
- `backend/app/application/services/email_notification_service.py` - Core service implementation

## Overview

The Email Notifications System provides a subscription-based notification service that allows users to opt into email alerts for various entity lifecycle events and workflow state changes.

## Architecture

### Domain Model

```
┌─────────────────────────────────────┐
│   NotificationCatalogEntry          │
├─────────────────────────────────────┤
│   catalog_id: str                   │
│   title: str                        │
│   description: str                  │
│   entity_type: str                  │
│   event: str                        │
│   category: str                     │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│   NotificationSubscriptionService │
├─────────────────────────────────────┤
│   repo: NotificationSubscriptionRepository │
└─────────────────────────────────────┘

Subscription Record:
{
  "id": "NS-a1b2c3d4e5f67890",
  "user_id": "USR-001",
  "entity_type": "purchase_request",
  "event": "created",
  "recipient_email": "user@example.com",
  "is_active": true
}
```

**Key Fields:**

- `catalog_id`: Unique identifier (e.g., `email.purchase_request.created`)
- `title`: Display title in Title Case (e.g., "Purchase Request: New Record")
- `description`: Human-readable description of when the notification fires
- `entity_type`: Entity slug (e.g., `purchase_request`, `work_order`)
- `event`: Event type (`created`, `workflow_state:*`, `scheduler_created`, `below_threshold`)
- `category`: Grouping category (e.g., "Purchasing", "Work Management", "Maintenance")

### Supported Entities & Events

| Entity                | Events                                        | Category        |
| --------------------- | --------------------------------------------- | --------------- |
| `purchase_request`    | created, workflow_state:\*                    | Purchasing      |
| `work_order`          | created, workflow_state:\*                    | Work Management |
| `maintenance_request` | created, workflow_state:\*, scheduler_created | Maintenance     |
| `item`                | below_threshold                               | Inventory       |

### Workflow States (per Entity)

**Purchase Request:** Draft, Pending Review, Pending Approval, Approved, Closed, Rejected  
**Work Order:** Requested, Approved, In Progress, Closed  
**Maintenance Request:** Draft, Pending Approval, Approved, Release, Completed

## Backend Components

### Catalog Definition

**Location:** `backend/app/application/email_notifications/catalog.py`

The catalog is a developer-maintained list of all available notifications. Each entry defines when and why a notification fires.

```python
def _build_catalog() -> tuple[NotificationCatalogEntry, ...]:
    # Example entry
    NotificationCatalogEntry(
        catalog_id="email.purchase_request.created",
        title="Purchase Request: New Record",
        description="Email when a new purchase request is created.",
        entity_type="purchase_request",
        event="created",
        category="Purchasing",
    )
```

### API Endpoints

**Base:** `/api/v1/notifications`

| Endpoint              | Method | Description                           |
| --------------------- | ------ | ------------------------------------- |
| `/catalog`            | GET    | List all available notification types |
| `/subscriptions`      | GET    | List current user's subscriptions     |
| `/subscriptions`      | POST   | Subscribe to a notification           |
| `/subscriptions/{id}` | DELETE | Unsubscribe from a notification       |

### Email Service Orchestrator

**Location:** `backend/app/application/services/email_notification_service.py`

Orchestrates email delivery by:

1. Resolving recipient list from subscription matches
2. Generating human-readable subject lines
3. Building message content from templates
4. Triggering async email delivery via SMTP

**Template Locations:**

- `backend/app/templates/email/base.html` - Base template with modern styling
- `backend/app/templates/email/record_notification.html` - Record event notification

**Event Types:**

| Event Type          | Subject Prefix            | Description               |
| ------------------- | ------------------------- | ------------------------- |
| `created`           | `New:`              | New record created        |
| `updated`           | `Updated:`          | Record updated            |
| `workflow_changed`  | `Status Changed:`   | Status changed            |
| `workflow_state:*`  | `Workflow {State}:` | Specific state transition |
| `scheduler_created` | `Scheduled:`        | Scheduler created         |
| `below_threshold`   | `Low stock:`        | Inventory alert           |

### Subscription Service API

**Base:** `/api/v1/notifications`

| Endpoint              | Method | Description                           |
| --------------------- | ------ | ------------------------------------- |
| `/catalog`            | GET    | List all available notification types |
| `/subscriptions`      | GET    | List current user's subscriptions     |
| `/subscriptions`      | POST   | Subscribe to a notification           |
| `/subscriptions/{id}` | DELETE | Unsubscribe from a notification       |

### Database Schema

**notification_subscription Table:**

| Column            | Type      | Description                                |
| ----------------- | --------- | ------------------------------------------ |
| `id`              | VARCHAR   | Primary key (format: `NS-{uuid}`)          |
| `user_id`         | VARCHAR   | Foreign key to users table                 |
| `entity_type`     | VARCHAR   | Entity slug (e.g., "purchase_request")     |
| `event`           | VARCHAR   | Event type (e.g., "created")               |
| `entity_id`       | VARCHAR   | Optional specific entity ID (null for all) |
| `recipient_email` | VARCHAR   | Email address for notifications            |
| `is_active`       | BOOLEAN   | Subscription status                        |
| `created_at`      | TIMESTAMP | Creation time                              |
| `updated_at`      | TIMESTAMP | Last update                                |

**Indexes:**

- `(user_id, entity_type, event)` - Unique constraint
- `(entity_type, event, is_active)` - For recipient resolution

### Subscription Operations

**Subscribe by Catalog ID:**

```python
async def subscribe_by_catalog_id(
    user_id: str,
    user_email: str,
    catalog_id: str,
) -> dict
```

- Validates catalog entry exists
- Reactivates existing subscription if found
- Creates new subscription if not exists

**Resolve Recipients:**

```python
async def resolve_recipients(
    entity_type: str,
    event: str,
    entity_id: Optional[str] = None,
) -> list[str]
```

Returns email addresses of subscribed users for entity/event.

**Unsubscribe:**

```python
async def unsubscribe(
    user_id: str,
    subscription_id: str,
) -> bool
```

Validates ownership and deletes subscription.

## Frontend Components

### Data Table

**Location:** `frontend/app/pages/notifications.vue`

The notifications page displays all available notifications in a data table with:

| Column       | Type                | Description                                         |
| ------------ | ------------------- | --------------------------------------------------- |
| Notification | title + description | What the notification is for                        |
| Category     | UBadge              | Entity category (Purchasing, Work Management, etc.) |
| Status       | UBadge              | Active (green) / Inactive (gray) subscription state |
| Action       | UButton             | Subscribe/Unsubscribe toggle                        |

**Table Configuration:**

```typescript
const tableColumns = [
  { accessorKey: "title", header: "Notification" },
  { accessorKey: "category", header: "Category" },
  { accessorKey: "status", header: "Status" },
  { accessorKey: "action", header: "Action" },
];
```

### Subscription Logic

```typescript
// Check if user is subscribed to a catalog entry
function isSubscribed(entry: NotificationCatalogEntry): boolean {
  return !!rowForEntry(entry);
}

// Match subscription by entity_type + event routing keys
function rowForEntry(
  entry: NotificationCatalogEntry,
): Subscription | undefined {
  return mine.value.find(
    (s) =>
      subscriptionActive(s) &&
      s.entity_type === entry.entity_type &&
      s.event === entry.event,
  );
}
```

### State Management

- `catalog`: All available `NotificationCatalogEntry` items from API
- `mine`: User's current `Subscription[]` from API
- `loading`: Boolean for table loading state
- `savingId`: Tracks which subscription action is in-progress

## User Flow

1. **View Page**: User navigates to `/notifications`
2. **Loading**: Table shows skeleton rows with carousel animation
3. **Display**: All notifications render with category badges
4. **Check Status**: Green "Active" badge if subscribed, gray "Inactive" if not
5. **Toggle**: Click Subscribe/Unsubscribe button to change state
6. **Feedback**: Toast notification confirms action success/error

## Integration Points

### From Entity Lifecycle

Notifications fire from entity service hooks:

```python
# After document insert
await email_notification_service.notify_document_change(
    entity_type="purchase_request",
    entity_id=doc.id,
    event_type="created",
    actor_user_id=user.id,
)

# After workflow state change
await email_notification_service.notify_document_change(
    entity_type="work_order",
    entity_id=doc.id,
    event_type=f"workflow_state:{new_state}",
    actor_user_id=user.id,
)
```

### From Scheduler

Maintenance scheduler creates notifications for auto-generated requests:

```python
await email_notification_service.notify_document_change(
    entity_type="maintenance_request",
    entity_id=new_request.id,
    event_type="scheduler_created",
    actor_user_id="scheduler",
)
```

## Configuration

No special configuration required. The system uses:

- User's profile email (`authStore.user.email`)
- Async email delivery via internal queue
- In-app toast notifications for user feedback

## Testing

**Unit Tests:** `backend/tests/test_email_notification.py`

Test scenarios:

- Catalog entry lookup by ID
- Subscription matching logic
- Email template rendering
- Notification triggering from entity changes

**Manual Testing:**

1. Subscribe to "Purchase Request: New Record"
2. Create a new purchase request
3. Verify email received at user's email address
4. Unsubscribe and verify no further emails

## Future Enhancements

Potential improvements:

- In-app notification bell/indicator
- Notification batching (digest mode)
- Custom notification templates per user
- Webhook support for external integrations
- Notification history/audit log

## Maintenance

**Update Triggers**:

- Notification catalog changes
- New entity types added
- Subscription workflow updates
- Email template modifications
- Integration point changes
- Delivery mechanism updates

**Verification**:

- Run `pytest tests/test_email_notification.py` - all tests must pass
- Test catalog entry lookup by ID
- Verify subscription matching logic
- Test email template rendering
- Check notification triggering from entity changes
- Validate manual testing workflow
- Confirm frontend notification UI functionality

**Last Updated**: 2026-04-05

## References

- Nuxt UI Table: https://ui.nuxt.com/components/table
- TanStack Table: https://tanstack.com/table/latest
- FastAPI Background Tasks: Used for async email delivery
