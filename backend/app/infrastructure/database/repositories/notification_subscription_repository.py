from typing import Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.framework.models.auth import User
from app.core.framework.models.infrastructure import NotificationSubscription


class NotificationSubscriptionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_user(self, user_id: str) -> list[NotificationSubscription]:
        result = await self.db.execute(
            select(NotificationSubscription)
            .where(NotificationSubscription.user_id == user_id)
            .order_by(
                NotificationSubscription.entity_type.asc(),
                NotificationSubscription.event.asc(),
            )
        )
        return list(result.scalars().all())

    async def get_by_user_entity_event(
        self,
        user_id: str,
        entity_type: str,
        event: str,
    ) -> Optional[NotificationSubscription]:
        result = await self.db.execute(
            select(NotificationSubscription).where(
                NotificationSubscription.user_id == user_id,
                NotificationSubscription.entity_type == entity_type,
                NotificationSubscription.event == event,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, subscription_id: str) -> Optional[NotificationSubscription]:
        result = await self.db.execute(
            select(NotificationSubscription).where(NotificationSubscription.id == subscription_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> NotificationSubscription:
        record = NotificationSubscription(**data)
        self.db.add(record)
        await self.db.commit()
        return record

    async def update(self, subscription_id: str, data: dict) -> Optional[NotificationSubscription]:
        record = await self.get_by_id(subscription_id)
        if not record:
            return None
        for key, value in data.items():
            if hasattr(record, key):
                setattr(record, key, value)
        await self.db.commit()
        return record

    async def delete(self, subscription_id: str) -> bool:
        record = await self.get_by_id(subscription_id)
        if not record:
            return False
        await self.db.delete(record)
        await self.db.commit()
        return True

    async def resolve_recipients(
        self,
        entity_type: str,
        event: str,
        entity_id: Optional[str] = None,
    ) -> list[str]:
        stmt = (
            select(User.email)
            .join(NotificationSubscription, NotificationSubscription.user_id == User.id)
            .where(
                NotificationSubscription.entity_type == entity_type,
                NotificationSubscription.event == event,
                NotificationSubscription.is_active == True,
                User.is_active == True,
                User.email.isnot(None),
                or_(
                    NotificationSubscription.entity_id.is_(None),
                    NotificationSubscription.entity_id == "",
                    NotificationSubscription.entity_id == entity_id,
                ),
            )
            .distinct()
        )
        result = await self.db.execute(stmt)
        emails = [e for e in result.scalars().all() if e]
        return sorted(set(emails))
