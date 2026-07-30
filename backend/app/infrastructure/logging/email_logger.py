"""
Email Logger
=============
Logs every email send attempt to the email_log entity table.
Infrastructure layer — depends on database, not on application services.
"""
import logging
import traceback
from datetime import datetime
from typing import Optional

from app.core.database import async_session_maker
from app.domain.protocols.email_service import EmailMessage, EmailResult

logger = logging.getLogger(__name__)


async def log_email_send(
    message: EmailMessage,
    result: EmailResult,
    entity_name: Optional[str] = None,
    record_id: Optional[str] = None,
    event_type: Optional[str] = None,
    sent_by: Optional[str] = None,
    error_traceback: Optional[str] = None,
) -> None:
    """Persist an email send attempt to the email_log table."""
    from app.infrastructure.database.repositories.entity_repository import get_entity_model

    try:
        async with async_session_maker() as db:
            model = get_entity_model("email_log")
            if not model:
                logger.warning("email_log model not found — skipping email logging")
                return

            log_entry = model(
                subject=message.subject,
                recipients=", ".join(message.to),
                cc=", ".join(message.cc) if message.cc else None,
                bcc=", ".join(message.bcc) if message.bcc else None,
                from_address=None,
                entity_name=entity_name,
                record_id=record_id,
                event_type=event_type,
                status="success" if result.success else "error",
                error_message=result.message if not result.success else None,
                error_traceback=error_traceback if not result.success else None,
                html_body=message.html_body[:5000] if message.html_body else None,
                recipient_count=result.recipient_count or len(message.to),
                sent_at=datetime.now(),
                sent_by=sent_by,
            )
            db.add(log_entry)
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to log email send: {e}")
