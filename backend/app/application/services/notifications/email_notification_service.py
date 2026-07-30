"""
Email Notification Service
============================
Application-layer orchestrator for sending email notifications.
Composes email content from entity records and sends via the email service.
Depends on domain protocols, not concrete implementations.
"""
import logging
from typing import Any, Optional
from datetime import datetime, date

from app.domain.protocols.email_service import (
    EmailServiceProtocol,
    EmailTemplateRendererProtocol,
    EmailMessage,
    EmailResult,
)
from app.application.services.notifications.notification_subscription_service import NotificationSubscriptionService
from app.application.services.documents.document_service import DocumentAppService
from app.infrastructure.database.repositories.document_repository import DocumentRepository
from app.meta.registry import MetaRegistry

logger = logging.getLogger(__name__)


class EmailNotificationService:
    """Orchestrates building and sending entity-based email notifications."""

    def __init__(
        self,
        email_service: EmailServiceProtocol,
        template_renderer: EmailTemplateRendererProtocol,
        notification_subscription_service: NotificationSubscriptionService,
    ):
        self._email_service = email_service
        self._template_renderer = template_renderer
        self._notification_subscription_service = notification_subscription_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def send_record_notification(
        self,
        entity_name: str,
        record: dict[str, Any],
        db,
        recipients: Optional[list[str]] = None,
        event_type: str = "created",
        custom_message: Optional[str] = None,
        action_url: Optional[str] = None,
    ) -> EmailResult:
        """
        Send an email notification about an entity record event.

        Args:
            entity_name: Snake-case entity name (e.g. 'purchase_request').
            record: The record data dict.
            recipients: List of email addresses.
            event_type: One of 'created', 'updated', 'workflow_changed', 'action', etc.
            custom_message: Optional override for the body message.
            action_url: Optional deep-link URL to the record in the frontend.
        """
        resolved_recipients = recipients or await self._notification_subscription_service.resolve_recipients(
            entity_type=entity_name,
            event=event_type,
            entity_id=record.get("id"),
        )

        if not resolved_recipients:
            return EmailResult(success=False, message="No recipients provided", recipient_count=0)

        meta = MetaRegistry.get(entity_name)
        entity_label = meta.label if meta else entity_name.replace("_", " ").title()

        record_id = record.get("id", "N/A")
        # Handle case where db is None (e.g., test emails)
        if db is not None:
            document_repo = DocumentRepository(db)
            document_service = DocumentAppService(document_repo)
            record_display = await document_service.get_record_display_name(entity_name, record)
            visible_name = record_display or str(record_id)
        else:
            visible_name = str(record_id)
        subject = self._build_subject(entity_label, visible_name, event_type)
        greeting = "Hello,"
        message = custom_message or self._build_default_message(
            entity_label, visible_name, event_type
        )

        record_fields = self._format_record_fields(entity_name, record, meta)

        html_body = self._template_renderer.render(
            "record_notification.html",
            {
                "subject": subject,
                "subtitle": f"{entity_label} • {visible_name}",
                "greeting": greeting,
                "message": message,
                "record_fields": record_fields,
                "entity_label": entity_label,
                "action_url": action_url,
            },
        )

        email = EmailMessage(
            to=resolved_recipients,
            subject=subject,
            html_body=html_body,
            plain_body=self._build_plain_text(entity_label, visible_name, message, record_fields),
        )

        result = await self._email_service.send(email)

        # Log the email send attempt
        try:
            from app.infrastructure.logging.email_logger import log_email_send
            await log_email_send(
                message=email,
                result=result,
                entity_name=entity_name,
                record_id=str(record_id),
                event_type=event_type,
            )
        except Exception:
            logger.warning("Failed to log email send attempt", exc_info=True)

        return result

    async def send_custom_email(
        self,
        recipients: list[str],
        subject: str,
        html_body: str,
        plain_body: Optional[str] = None,
    ) -> EmailResult:
        """Send a fully custom email (no template rendering)."""
        if not recipients:
            return EmailResult(success=False, message="No recipients provided", recipient_count=0)

        email = EmailMessage(
            to=recipients,
            subject=subject,
            html_body=html_body,
            plain_body=plain_body,
        )
        result = await self._email_service.send(email)

        # Log the email send attempt
        try:
            from app.infrastructure.logging.email_logger import log_email_send
            await log_email_send(message=email, result=result)
        except Exception:
            logger.warning("Failed to log custom email send attempt", exc_info=True)

        return result

    async def send_test_email(self, recipient: str) -> EmailResult:
        """Send a test email to verify SMTP configuration."""
        sample_record = {
            "id": "TEST-00001",
            "name": "Sample Core Record",
            "description": "Example record from the core framework.",
            "created_at": datetime.now().isoformat(),
        }

        from app.core.config import settings

        base = (settings.PUBLIC_APP_URL or "").rstrip("/")
        sample_url = f"{base}/record/TEST-00001" if base else None
        return await self.send_record_notification(
            entity_name="core_record",
            record=sample_record,
            db=None,
            recipients=[recipient],
            event_type="created",
            custom_message=(
                "This is a <b>test email</b> from the core notification service. "
                "Below is a sample record to demonstrate the email format."
            ),
            action_url=sample_url,
        )

    async def resolve_subscribed_emails(
        self,
        entity_type: str,
        event: str,
        entity_id: Optional[str] = None,
    ) -> list[str]:
        """Emails for users subscribed to this entity/event (via notification_subscription)."""
        return await self._notification_subscription_service.resolve_recipients(
            entity_type=entity_type,
            event=event,
            entity_id=entity_id,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _workflow_state_pretty(event_type: str) -> Optional[str]:
        if not event_type.startswith("workflow_state:"):
            return None
        rest = event_type.split(":", 1)[1]
        return rest.replace("_", " ").title()

    @staticmethod
    def _build_subject(entity_label: str, record_id: str, event_type: str) -> str:
        wf = EmailNotificationService._workflow_state_pretty(event_type)
        if wf:
            return f"[EAM] Workflow {wf}: {entity_label} {record_id}"
        event_labels = {
            "created": "New",
            "updated": "Updated",
            "workflow_changed": "Status Changed",
            "action": "Action Required",
            "deleted": "Deleted",
            "scheduler_created": "Scheduled",
            "below_threshold": "Low stock",
        }
        prefix = event_labels.get(event_type, event_type.replace("_", " ").title())
        return f"[EAM] {prefix}: {entity_label} {record_id}"

    @staticmethod
    def _build_default_message(entity_label: str, record_id: str, event_type: str) -> str:
        wf = EmailNotificationService._workflow_state_pretty(event_type)
        if wf:
            return (
                f"The {entity_label} ({record_id}) moved to workflow state "
                f"{wf}."
            )
        templates = {
            "created": f"A new {entity_label} ({record_id}) has been created and is ready for review.",
            "updated": f"The {entity_label} ({record_id}) has been updated.",
            "workflow_changed": f"The status of {entity_label} ({record_id}) has changed.",
            "action": f"An action is required on {entity_label} ({record_id}).",
            "deleted": f"The {entity_label} ({record_id}) has been deleted.",
            "scheduler_created": (
                f"A planned {entity_label} ({record_id}) was created by the maintenance scheduler."
            ),
            "below_threshold": (
                f"{entity_label} alert for {record_id}: review stock levels in the application."
            ),
        }
        return templates.get(
            event_type,
            f"A notification was triggered for {entity_label} ({record_id}).",
        )

    @staticmethod
    def _format_record_fields(
        entity_name: str,
        record: dict[str, Any],
        meta: Any,
    ) -> list[dict[str, str]]:
        """Build a list of {name, label, value} dicts for template rendering."""
        skip_fields = {"hashed_password", "updated_at"}
        fields = []

        if meta and meta.fields:
            for f in meta.fields:
                name = f.name
                if name in skip_fields:
                    continue
                value = record.get(name)
                if value is None:
                    continue
                if isinstance(value, (datetime, date)):
                    value = value.isoformat()
                fields.append({
                    "name": name,
                    "label": f.label or name.replace("_", " ").title(),
                    "value": str(value),
                })
        else:
            for key, value in record.items():
                if key in skip_fields:
                    continue
                if value is None:
                    continue
                if isinstance(value, (datetime, date)):
                    value = value.isoformat()
                fields.append({
                    "name": key,
                    "label": key.replace("_", " ").title(),
                    "value": str(value),
                })

        return fields

    @staticmethod
    def _build_plain_text(
        entity_label: str,
        record_id: str,
        message: str,
        record_fields: list[dict[str, str]],
    ) -> str:
        """Build a plain-text fallback for the email."""
        import re
        clean_msg = re.sub(r"<[^>]+>", "", message)
        lines = [
            f"{entity_label} — {record_id}",
            "",
            clean_msg,
            "",
            "Record Details:",
            "-" * 40,
        ]
        for field in record_fields:
            lines.append(f"  {field['label']}: {field['value']}")
        lines.append("-" * 40)
        lines.append("")
        lines.append("This is an automated notification from the system.")
        return "\n".join(lines)
