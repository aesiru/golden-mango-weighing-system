import uuid
from datetime import datetime
from typing import Optional

from app.application.email_notifications.catalog import require_catalog_entry
from app.core.serialization import record_to_dict
from app.infrastructure.database.repositories.notification_subscription_repository import (
    NotificationSubscriptionRepository,
)


class NotificationSubscriptionService:
    def __init__(self, repo: NotificationSubscriptionRepository):
        self.repo = repo

    async def list_catalog_subscriptions_for_user(self, user_id: str) -> list[dict]:
        rows = await self.repo.list_for_user(user_id)
        return [record_to_dict(row) for row in rows]

    async def subscribe_by_catalog_id(self, user_id: str, user_email: str, catalog_id: str) -> dict:
        entry = require_catalog_entry(catalog_id)
        email_norm = str(user_email).strip().lower()
        existing = await self.repo.get_by_user_entity_event(
            user_id, entry.entity_type, entry.event
        )
        if existing:
            updated = await self.repo.update(
                existing.id,
                {"is_active": True, "recipient_email": email_norm},
            )
            return record_to_dict(updated) if updated else record_to_dict(existing)

        record = await self.repo.create(
            {
                "id": f"NS-{uuid.uuid4().hex[:16]}",
                "user_id": user_id,
                "entity_type": entry.entity_type,
                "event": entry.event,
                "entity_id": None,
                "recipient_email": email_norm,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        )
        return record_to_dict(record)

    async def unsubscribe(self, user_id: str, subscription_id: str) -> bool:
        record = await self.repo.get_by_id(subscription_id)
        if not record or record.user_id != user_id:
            return False
        return await self.repo.delete(subscription_id)

    async def resolve_recipients(
        self,
        entity_type: str,
        event: str,
        entity_id: Optional[str] = None,
    ) -> list[str]:
        return await self.repo.resolve_recipients(
            entity_type=entity_type,
            event=event,
            entity_id=entity_id,
        )
