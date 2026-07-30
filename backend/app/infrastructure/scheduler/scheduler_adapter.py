"""Scheduler Adapter - Infrastructure layer for APScheduler."""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger("scheduler")


class SchedulerAdapter:
    """Infrastructure adapter for APScheduler."""

    def __init__(self):
        self._scheduler = AsyncIOScheduler()

    def add_job(self, func, trigger, id: str, name: str, replace_existing: bool = False):
        """Add a job to the scheduler."""
        self._scheduler.add_job(
            func,
            trigger,
            id=id,
            name=name,
            replace_existing=replace_existing,
        )

    def start(self):
        """Start the scheduler."""
        self._scheduler.start()

    def shutdown(self, wait: bool = True):
        """Shutdown the scheduler."""
        self._scheduler.shutdown(wait=wait)

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._scheduler.running

    def get_jobs(self):
        """Get all jobs from scheduler."""
        return self._scheduler.get_jobs()
