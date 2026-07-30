"""
Infrastructure Layer: Email Notification Factory

Builds EmailNotificationDispatcher with infrastructure components wired to a specific DB session.
Used from hooks and schedulers (non-Request contexts).

Clean Architecture Layer: Infrastructure
Responsibility: Wire infrastructure email services (SMTP, Jinja templates) into the application dispatcher
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.email_notifications.dispatcher import EmailNotificationDispatcher
from app.application.services.notifications.email_notification_service import EmailNotificationService
from app.application.services.notifications.notification_subscription_service import NotificationSubscriptionService
from app.infrastructure.database.repositories.notification_subscription_repository import (
    NotificationSubscriptionRepository,
)
from app.infrastructure.email.smtp_service import SmtpEmailService
from app.infrastructure.email.template_renderer import JinjaEmailTemplateRenderer


def build_email_notification_dispatcher(db: AsyncSession) -> EmailNotificationDispatcher:
    """Build an EmailNotificationDispatcher with infrastructure components wired in."""
    repo = NotificationSubscriptionRepository(db)
    sub_svc = NotificationSubscriptionService(repo)
    email_svc = EmailNotificationService(
        email_service=SmtpEmailService(),
        template_renderer=JinjaEmailTemplateRenderer(),
        notification_subscription_service=sub_svc,
    )
    return EmailNotificationDispatcher(email_svc)
