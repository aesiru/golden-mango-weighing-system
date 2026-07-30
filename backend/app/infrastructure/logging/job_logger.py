"""
Scheduled Job Logger
=====================
Logs every scheduled job execution to the scheduled_job_log entity table.
Infrastructure layer — depends on database, not on application services.
"""
import logging
import traceback
from datetime import datetime
from typing import Optional

from app.core.database import async_session_maker

logger = logging.getLogger(__name__)


async def log_job_execution(
    job_id: str,
    job_name: str,
    status: str,
    started_at: datetime,
    completed_at: Optional[datetime] = None,
    duration_seconds: Optional[float] = None,
    records_created: int = 0,
    records_updated: int = 0,
    error_message: Optional[str] = None,
    error_traceback_str: Optional[str] = None,
    details: Optional[str] = None,
    trigger_type: str = "Cron",
    cron_expression: Optional[str] = None,
) -> None:
    """Persist a scheduled job execution to the scheduled_job_log table."""
    from app.infrastructure.database.repositories.entity_repository import get_entity_model

    try:
        async with async_session_maker() as db:
            model = get_entity_model("scheduled_job_log")
            if not model:
                logger.warning("scheduled_job_log model not found — skipping job logging")
                return

            log_entry = model(
                job_id=job_id,
                job_name=job_name,
                status=status,
                started_at=started_at,
                completed_at=completed_at or datetime.now(),
                duration_seconds=duration_seconds,
                records_created=records_created,
                records_updated=records_updated,
                error_message=error_message,
                error_traceback=error_traceback_str,
                details=details,
                trigger_type=trigger_type,
                cron_expression=cron_expression,
            )
            db.add(log_entry)
            await db.commit()
    except Exception as e:
        logger.error(f"Failed to log job execution: {e}")
