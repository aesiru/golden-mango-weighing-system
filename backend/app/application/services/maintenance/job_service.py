"""
Application Layer: Maintenance Job Service

Wraps maintenance job automation functions from the module API layer.
Provides a clean application service interface for maintenance job operations.

Clean Architecture Layer: Application
Responsibility: Orchestrate maintenance job creation and scheduling
"""
import logging
import traceback
from datetime import date, datetime, timedelta
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker

logger = logging.getLogger("maintenance_automation")

# All maintenance module APIs removed - service disabled
# Future modules can implement their own job services


class MaintenanceJobService:
    """Application service for maintenance job operations."""

    async def test_scheduler_every_minute(self) -> None:
        """Test function to validate scheduler works. Creates a simple log entry every minute."""
        logger.info("⏰ Test scheduler running - creating test record...")
        started_at = datetime.now()

        async with async_session_maker() as db:
            try:
                test_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                logger.info(f"✅ Scheduler test executed at {test_time}")
                await self._log_job(
                    "test_scheduler_every_minute",
                    "Test Scheduler (Every Minute)",
                    started_at,
                    "Success",
                    details=f"Test ping at {test_time}",
                    cron_expression="* * * * *",
                )
            except Exception as exc:
                logger.error(f"❌ Test scheduler error: {exc}")
                await db.rollback()
                await self._log_job(
                    "test_scheduler_every_minute",
                    "Test Scheduler (Every Minute)",
                    started_at,
                    "Error",
                    error_message=str(exc),
                    error_tb=self._format_error_trace(),
                    cron_expression="* * * * *",
                )

    async def _log_job(
        self,
        job_id: str,
        job_name: str,
        started_at: datetime,
        status: str,
        records_created: int = 0,
        records_updated: int = 0,
        error_message: str | None = None,
        error_tb: str | None = None,
        details: str | None = None,
        trigger_type: str = "Cron",
        cron_expression: str | None = None,
    ) -> None:
        """Log job execution to the job logger."""
        try:
            from app.infrastructure.logging.job_logger import log_job_execution

            completed = datetime.now()
            duration = (completed - started_at).total_seconds()
            await log_job_execution(
                job_id=job_id,
                job_name=job_name,
                status=status,
                started_at=started_at,
                completed_at=completed,
                duration_seconds=duration,
                records_created=records_created,
                records_updated=records_updated,
                error_message=error_message,
                error_traceback_str=error_tb,
                details=details,
                trigger_type=trigger_type,
                cron_expression=cron_expression,
            )
        except Exception as exc:
            logger.warning(f"Failed to log job execution: {exc}")

    def _format_error_trace(self) -> str:
        """Format error traceback for logging."""
        return traceback.format_exc()

    # All maintenance generation functions removed - modules deleted
    async def run_calendar_generation(self) -> None:
        """Run maintenance calendar generation - DISABLED (modules removed)."""
        logger.info("Calendar generation disabled - maintenance modules removed")

    async def run_condition_generation(self) -> None:
        """Run maintenance condition generation - DISABLED (modules removed)."""
        logger.info("Condition generation disabled - maintenance modules removed")

    async def run_interval_generation(self) -> None:
        """Run maintenance interval generation - DISABLED (modules removed)."""
        logger.info("Interval generation disabled - maintenance modules removed")

    async def create_work_package(
        self,
        db: AsyncSession,
        *,
        activity_name: str,
        pma_id: Optional[str] = None,
        asset_id: Optional[str] = None,
        location_id: Optional[str] = None,
        site: Optional[str] = None,
        department: Optional[str] = None,
        due_date: date,
        description: str,
        request_type: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> tuple[str, str, str]:
        """Create a work package (maintenance request + work order activity)."""
        from app.application.services.documents.document import new_doc, save_doc

        woa = await new_doc(
            "work_order_activity",
            db,
            workflow_state="awaiting_resources",
            work_order=None,
            description=activity_name or description,
            work_item_type="Asset" if asset_id else "Non-Asset",
            work_item=asset_id,
            location=location_id,
            site=site,
            department=department,
            start_date=datetime.combine(due_date, datetime.min.time()),
            end_date=datetime.combine(due_date, datetime.min.time()) + timedelta(minutes=30),
            activity_type=request_type,
        )
        woa = await save_doc(woa, db, commit=False)

        mr = await new_doc(
            "maintenance_request",
            db,
            workflow_state="Approved",
            due_date=due_date,
            description=description,
            planned_maintenance_activity=pma_id,
            asset=asset_id,
            location=location_id,
            site=site,
            department=department,
            request_type=request_type,
            priority=priority,
            work_order_activity=woa.id,
        )
        mr = await save_doc(mr, db, commit=False)

        try:
            from app.infrastructure.email.notification_factory import build_email_notification_dispatcher
            from app.core.config import settings
            from app.core.serialization import record_to_dict

            mr_dict = record_to_dict(mr)
            dispatch = build_email_notification_dispatcher(db)
            base = (settings.PUBLIC_APP_URL or "").rstrip("/")
            rid = mr_dict.get("id")
            action_url = f"{base}/maintenance_request/{rid}" if base and rid else None
            await dispatch.notify(
                "email.maintenance_request.scheduler_created",
                mr_dict,
                action_url=action_url,
            )
        except Exception:
            logger.warning(
                "scheduler maintenance_request email notification failed", exc_info=True
            )

        return mr.id, woa.id, None

    async def create_work_order_from_request(
        self,
        db: AsyncSession,
        *,
        maint_req: Any,
        activity_name: str,
        asset_id: Optional[str],
        location_id: Optional[str],
        site: Optional[str],
        department: Optional[str],
        due_date: date,
        description: str,
        request_type: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> tuple[str, str]:
        """Create a work order from a maintenance request."""
        from app.application.services.documents.document import new_doc, save_doc

        wo = await new_doc(
            "work_order",
            db,
            workflow_state="requested",
            work_order_type="Preventive Maintenance" if request_type else None,
            description=description,
            due_date=due_date,
            priority=priority,
            site=site,
            department=department,
        )
        wo = await save_doc(wo, db, commit=False)

        woa = await new_doc(
            "work_order_activity",
            db,
            workflow_state="awaiting_resources",
            work_order=wo.id,
            description=activity_name or description,
            work_item_type="Asset" if asset_id else "Non-Asset",
            work_item=asset_id,
            location=location_id,
            site=site,
            department=department,
            start_date=datetime.combine(due_date, datetime.min.time()),
            end_date=datetime.combine(due_date, datetime.min.time()) + timedelta(minutes=30),
            activity_type=request_type,
        )
        woa = await save_doc(woa, db, commit=False)

        maint_req.work_order_activity = woa.id
        await save_doc(maint_req, db, commit=False)
        await db.commit()

        return wo.id, woa.id

    def parse_threshold_value(self, property_type: Optional[str], value: Optional[str]):
        """Parse a threshold value based on its property type."""
        if value is None:
            return None
        try:
            if property_type in ("Numeric", "Float", "Int", "Integer"):
                return float(value)
            if property_type in ("Date",):
                return date.fromisoformat(str(value)[:10])
            if property_type in ("Datetime",):
                return datetime.fromisoformat(str(value))
        except Exception:
            return None
        return None
