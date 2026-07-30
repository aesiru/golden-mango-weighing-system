"""
Setup Routes
=============
First-run setup wizard endpoints.
On a fresh install (no users in DB), allows creating the initial superuser
without authentication and optionally seeding reference data.

API contract (unchanged):
  GET  /setup/status        → {is_setup_complete, needs_setup}
  POST /setup/create-admin  → creates superadmin; optionally runs full seed pipeline
"""
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.application.services.setup_service import SetupService

router = APIRouter(tags=["setup"])


class SetupAdminRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=6)
    run_seeds: bool = Field(
        True,
        description="When true, seeds roles, workflow states/actions, and reference data after admin creation.",
    )


def _setup_service(db: AsyncSession = Depends(get_db)) -> SetupService:
    return SetupService(db)


@router.get("/setup/status")
async def setup_status(svc: SetupService = Depends(_setup_service)):
    """Check whether the system already has users (setup complete) or not."""
    status = await svc.get_status()
    return {
        "is_setup_complete": status.is_setup_complete,
        "needs_setup": status.needs_setup,
    }


@router.post("/setup/create-admin")
async def create_admin(
    data: SetupAdminRequest,
    svc: SetupService = Depends(_setup_service),
):
    """
    Create the first administrator account.
    Only works on a fresh system (no users exist).
    Optionally seeds all reference data in the same request.
    """
    try:
        setup_result = await svc.run_initial_setup(
            username=data.username,
            email=data.email,
            full_name=data.full_name,
            password=data.password,
            run_seeds=data.run_seeds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

    response = {
        "status": "success",
        "message": "Administrator account created successfully. You can now log in.",
        "data": {
            "username": setup_result.admin_username,
            "email": setup_result.admin_email,
            "full_name": setup_result.admin_full_name,
        },
    }

    if setup_result.seed_summary:
        response["seed_summary"] = {
            "total_created": setup_result.seed_summary.total_created,
            "total_skipped": setup_result.seed_summary.total_skipped,
            "entities": [
                {"entity": r.entity, "created": r.created, "skipped": r.skipped}
                for r in setup_result.seed_summary.results
            ],
        }

    return response
