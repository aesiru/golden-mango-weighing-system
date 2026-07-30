"""Scheduler Application Service."""
import logging
from typing import Optional
from apscheduler.triggers.cron import CronTrigger

from app.application.services.scheduling.job_registry import job_registry
from app.infrastructure.scheduler.scheduler_adapter import SchedulerAdapter

logger = logging.getLogger("scheduler")


class SchedulerAppService:
    """Application service for managing scheduled jobs."""

    def __init__(self, scheduler_adapter: SchedulerAdapter):
        self.scheduler_adapter = scheduler_adapter

    def start_scheduler(self):
        """Start the scheduler with all registered jobs."""
        jobs = job_registry.get_enabled_jobs()

        for job_id, job_def in jobs.items():
            try:
                trigger = self._parse_cron_expression(job_def.cron_expression)
                if trigger:
                    self.scheduler_adapter.add_job(
                        job_def.function,
                        trigger,
                        id=job_id,
                        name=job_def.description,
                        replace_existing=job_def.replace_existing,
                    )
                    logger.info(f"Scheduled job: {job_id} - {job_def.description}")
                else:
                    logger.warning(f"Invalid cron expression for job {job_id}: {job_def.cron_expression}")
            except Exception as e:
                logger.error(f"Failed to schedule job {job_id}: {str(e)}")

        self.scheduler_adapter.start()

        # Log summary
        enabled_count = len(jobs)
        logger.info(f"Scheduler started with {enabled_count} jobs:")
        for job_id, job_def in jobs.items():
            logger.info(f"  - {job_id}: {job_def.description} ({job_def.cron_expression})")

    def stop_scheduler(self):
        """Gracefully shut down the scheduler."""
        if self.scheduler_adapter.is_running():
            self.scheduler_adapter.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def get_scheduler_status(self) -> dict:
        """Get current scheduler status and job info."""
        if not self.scheduler_adapter.is_running():
            return {"status": "stopped", "jobs": []}

        jobs = []
        for job in self.scheduler_adapter.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            })

        return {
            "status": "running",
            "jobs": jobs
        }

    def _parse_cron_expression(self, cron_expr: str) -> Optional[CronTrigger]:
        """Parse cron expression to APScheduler trigger."""
        if cron_expr == "hourly":
            return CronTrigger(minute=0)
        elif cron_expr == "daily":
            return CronTrigger(hour=0, minute=0)
        elif cron_expr.startswith("daily at "):
            time_part = cron_expr.replace("daily at ", "")
            hour, minute = map(int, time_part.split(":"))
            return CronTrigger(hour=hour, minute=minute)
        elif cron_expr.startswith("cron(") and cron_expr.endswith(")"):
            inner = cron_expr[5:-1]
            parts = inner.split(",")
            kwargs = {}
            for part in parts:
                if "=" in part:
                    key, value = part.split("=")
                    kwargs[key.strip()] = int(value.strip())
            return CronTrigger(**kwargs)
        else:
            try:
                return CronTrigger.from_crontab(cron_expr)
            except:
                return None
