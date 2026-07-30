"""
Single entry point for feature code: notify by catalog_id only.
"""
from typing import Any, Optional

from app.application.email_notifications.catalog import require_catalog_entry
from app.application.services.notifications.email_notification_service import EmailNotificationService


class EmailNotificationDispatcher:
    def __init__(self, email_notification_service: EmailNotificationService):
        self._email = email_notification_service

    async def notify(
        self,
        catalog_id: str,
        record: dict[str, Any],
        *,
        action_url: Optional[str] = None,
        custom_message: Optional[str] = None,
    ):
        """Send a record-style email for subscribers of this catalog entry."""
        entry = require_catalog_entry(catalog_id)
        return await self._email.send_record_notification(
            entity_name=entry.entity_type,
            record=record,
            db=None,
            recipients=None,
            event_type=entry.event,
            custom_message=custom_message,
            action_url=action_url,
        )

    async def notify_if_configured(
        self,
        catalog_id: str,
        record: dict[str, Any],
        *,
        action_url: Optional[str] = None,
        custom_message: Optional[str] = None,
    ):
        """Like notify, but swallows unknown catalog_id (should not happen in production)."""
        try:
            return await self.notify(
                catalog_id,
                record,
                action_url=action_url,
                custom_message=custom_message,
            )
        except ValueError:
            from app.domain.protocols.email_service import EmailResult

            return EmailResult(success=False, message="Unknown catalog_id", recipient_count=0)

    async def send_custom_to_catalog_subscribers(
        self,
        catalog_id: str,
        *,
        subject: str,
        html_body: str,
        plain_body: Optional[str] = None,
    ):
        """Send a custom HTML email to all subscribers (e.g. inventory digest)."""
        entry = require_catalog_entry(catalog_id)
        recipients = await self._email.resolve_subscribed_emails(
            entity_type=entry.entity_type,
            event=entry.event,
        )
        if not recipients:
            from app.domain.protocols.email_service import EmailResult

            return EmailResult(success=False, message="No recipients", recipient_count=0)
        return await self._email.send_custom_email(
            recipients=recipients,
            subject=subject,
            html_body=html_body,
            plain_body=plain_body,
        )
