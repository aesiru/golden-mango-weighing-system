"""
Job Registry
============
Central registry for scheduled jobs across all modules.
Decouples scheduler from specific modules using Registry Pattern.
"""
from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass
from datetime import time
import logging

logger = logging.getLogger("job_registry")


@dataclass
class JobDefinition:
    """Definition of a scheduled job."""
    name: str
    function: Callable
    cron_expression: str
    description: str
    enabled: bool = True
    replace_existing: bool = True


class JobRegistry:
    """Registry for scheduled jobs using Registry Pattern."""
    
    def __init__(self):
        self._jobs: Dict[str, JobDefinition] = {}
    
    def register(
        self,
        job_id: str,
        function: Callable,
        cron_expression: str,
        description: str,
        enabled: bool = True,
        replace_existing: bool = True
    ) -> None:
        """
        Register a job with the registry.
        
        Args:
            job_id: Unique identifier for the job
            function: Async function to execute
            cron_expression: Cron trigger expression
            description: Human-readable description
            enabled: Whether job should be scheduled
            replace_existing: Whether to replace existing job
        """
        job = JobDefinition(
            name=job_id,
            function=function,
            cron_expression=cron_expression,
            description=description,
            enabled=enabled,
            replace_existing=replace_existing
        )
        
        self._jobs[job_id] = job
        logger.info(f"Registered job: {job_id} - {description}")
    
    def get_job(self, job_id: str) -> Optional[JobDefinition]:
        """Get a job definition by ID."""
        return self._jobs.get(job_id)
    
    def get_all_jobs(self) -> Dict[str, JobDefinition]:
        """Get all registered jobs."""
        return self._jobs.copy()
    
    def get_enabled_jobs(self) -> Dict[str, JobDefinition]:
        """Get only enabled jobs."""
        return {
            job_id: job for job_id, job in self._jobs.items()
            if job.enabled
        }
    
    def enable_job(self, job_id: str) -> bool:
        """Enable a job."""
        if job_id in self._jobs:
            self._jobs[job_id].enabled = True
            return True
        return False
    
    def disable_job(self, job_id: str) -> bool:
        """Disable a job."""
        if job_id in self._jobs:
            self._jobs[job_id].enabled = False
            return True
        return False
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a job from registry."""
        if job_id in self._jobs:
            del self._jobs[job_id]
            logger.info(f"Removed job: {job_id}")
            return True
        return False
    
    def list_jobs(self) -> None:
        """Log all registered jobs."""
        logger.info("=== Registered Jobs ===")
        for job_id, job in self._jobs.items():
            status = "ENABLED" if job.enabled else "DISABLED"
            logger.info(f"  {job_id}: {job.description} [{status}]")
            logger.info(f"    Schedule: {job.cron_expression}")
        logger.info("======================")


# Global registry instance
job_registry = JobRegistry()
