"""
Application Layer: App Initialization Service

Handles application startup and shutdown wiring, including scheduler initialization.
Encapsulates infrastructure component wiring from the main application entry point.

Clean Architecture Layer: Application
Responsibility: Wire infrastructure components and manage application lifecycle
"""
from app.infrastructure.scheduler.scheduler_adapter import SchedulerAdapter
from app.application.services.scheduling.scheduler import SchedulerAppService


class AppInitializationService:
    """Service for application initialization and shutdown."""

    def __init__(self):
        self.scheduler_service: SchedulerAppService | None = None

    def initialize_scheduler(self):
        """Initialize and start the scheduler with registered jobs."""
        scheduler_adapter = SchedulerAdapter()
        self.scheduler_service = SchedulerAppService(scheduler_adapter)
        self.scheduler_service.start_scheduler()

    def shutdown_scheduler(self):
        """Gracefully shut down the scheduler."""
        if self.scheduler_service:
            self.scheduler_service.stop_scheduler()
