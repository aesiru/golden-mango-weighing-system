"""
Test Scheduler API
==================
Manual trigger endpoints for testing scheduler functions.
"""
import logging
from fastapi import APIRouter
from app.application.services.maintenance.job_service import MaintenanceJobService

logger = logging.getLogger("scheduler_test")

router = APIRouter(prefix="/test", tags=["scheduler"])
maintenance_job_service = MaintenanceJobService()

@router.post("/scheduler/test-minute")
async def test_scheduler_minute():
    """Manually trigger the every-minute test function."""
    try:
        await maintenance_job_service.test_scheduler_every_minute()
        return {"status": "success", "message": "Test scheduler executed successfully"}
    except Exception as e:
        logger.error(f"Test scheduler failed: {e}")
        return {"status": "error", "message": str(e)}

@router.post("/scheduler/interval-check")
async def test_interval_check():
    """Manually trigger the daily maintenance interval check."""
    try:
        await maintenance_job_service.run_interval_generation()
        return {"status": "success", "message": "Daily maintenance interval check executed successfully"}
    except Exception as e:
        logger.error(f"Interval check failed: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/scheduler/calendar-check")
async def test_calendar_check():
    """Manually trigger the PM calendar auto-generation job."""
    try:
        await maintenance_job_service.run_calendar_generation()
        return {"status": "success", "message": "PM calendar auto-generation executed successfully"}
    except Exception as e:
        logger.error(f"Calendar check failed: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/scheduler/condition-check")
async def test_condition_check():
    """Manually trigger the daily maintenance condition check."""
    try:
        await maintenance_job_service.run_condition_generation()
        return {"status": "success", "message": "Daily maintenance condition check executed successfully"}
    except Exception as e:
        logger.error(f"Condition check failed: {e}")
        return {"status": "error", "message": str(e)}
