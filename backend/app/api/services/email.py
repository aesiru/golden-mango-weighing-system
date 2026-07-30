"""
Email Notification Routes
===========================
API endpoints for sending email notifications.
Thin HTTP layer — delegates to EmailNotificationService.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import get_email_notification_service
from app.application.services.notifications.email_notification_service import EmailNotificationService

router = APIRouter(prefix="/email", tags=["Email Notifications"])


@router.post("/send-test")
async def send_test_email(
    recipient: str = Body(..., embed=True),
    service: EmailNotificationService = Depends(get_email_notification_service),
):
    """Send a test email to verify SMTP configuration."""
    result = await service.send_test_email(recipient)
    return {
        "status": "success" if result.success else "error",
        "message": result.message,
        "recipient_count": result.recipient_count,
    }


@router.post("/notify")
async def send_record_notification(
    entity_name: str = Body(...),
    record_id: str = Body(...),
    recipients: Optional[list[str]] = Body(None),
    event_type: str = Body("created"),
    custom_message: Optional[str] = Body(None),
    action_url: Optional[str] = Body(None),
    db: AsyncSession = Depends(get_db),
    service: EmailNotificationService = Depends(get_email_notification_service),
):
    """
    Send an email notification about a specific entity record.
    Fetches the record from the database and formats it into an email.
    """
    from app.infrastructure.database.repositories.entity_repository import EntityRepository

    repo = EntityRepository(db)
    record = await repo.get_by_id(entity_name, record_id)
    if not record:
        return {"status": "error", "message": f"Record {record_id} not found in {entity_name}"}

    from app.core.serialization import record_to_dict
    record_dict = record_to_dict(record)

    result = await service.send_record_notification(
        entity_name=entity_name,
        record=record_dict,
        db=db,
        recipients=recipients or [],
        event_type=event_type,
        custom_message=custom_message,
        action_url=action_url,
    )
    return {
        "status": "success" if result.success else "error",
        "message": result.message,
        "recipient_count": result.recipient_count,
    }


@router.post("/send-custom")
async def send_custom_email(
    recipients: list[str] = Body(...),
    subject: str = Body(...),
    html_body: str = Body(...),
    plain_body: Optional[str] = Body(None),
    service: EmailNotificationService = Depends(get_email_notification_service),
):
    """Send a fully custom email."""
    result = await service.send_custom_email(
        recipients=recipients,
        subject=subject,
        html_body=html_body,
        plain_body=plain_body,
    )
    return {
        "status": "success" if result.success else "error",
        "message": result.message,
        "recipient_count": result.recipient_count,
    }
