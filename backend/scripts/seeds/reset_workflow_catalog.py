#!/usr/bin/env python3

import asyncio
from datetime import datetime

from sqlalchemy import delete

from app.core.database import async_session_maker
from app.core.framework.models.workflow import (
    Workflow,
    WorkflowAction,
    WorkflowState,
    WorkflowStateLink,
    WorkflowTransition,
    generate_slug,
)


STATES: list[str] = [
    "Draft",
    "Approved",
    "Partially Received",
    "Fully Received",
    "Cancelled",
    "Rejected",
    "Complete",
    "Open",
    "Closed",
    "Sourcing",
    "Review",
    "Awarded",
    "Ordered",
    "Submitted",
    "Posted",
    "Pending Approval",
    "Release",
    "Completed",
    "Planned",
    "In Progress",
    "Awaiting Resources",
    "Ready",
    "On Hold",
    "Requested",
    "Acquired",
    "Inspected",
    "Failed Inspection",
    "Active",
    "Inactive",
    "Under Maintenance",
    "Under Repair",
    "Decommissioned",
    "Disposed",
    "Pending Review",
    "Received",
    "Returned",
    "Issued",
]


ACTIONS: list[str] = [
    "Approve Line",
    "Reject Line",
    "Receive All Items",
    "Receive Partial Items",
    "Cancel",
    "Complete",
    "Approve",
    "Reject",
    "Submit Source",
    "Submit for Review",
    "Award",
    "Create Purchase Order",
    "Submit",
    "Post",
    "Submit for Approval",
    "Submit for Emergency",
    "Submit for Resolution",
    "Reopen",
    "Start Stock Count",
    "Allocate",
    "Start Activity",
    "Put On Hold",
    "Resume",
    "Close",
    "Start",
    "Inspect Asset",
    "Putaway",
    "Install Asset",
    "Commission",
    "Failed Inspection",
    "Maintain Asset",
    "Decommission",
    "Issue Equipment",
    "Retire Asset",
    "Internal Repair",
    "Send to Vendor",
    "Remove Asset",
    "Finish Repair",
    "Dispose",
    "Recommission",
    "Reject Purchase Request",
    "Revise Purchase Request",
    "Add Line Item",
    "Return Item",
    "Issue Item",
]


async def reset_workflow_catalog() -> None:
    async with async_session_maker() as db:
        # Delete dependent configuration first
        await db.execute(delete(WorkflowTransition))
        await db.execute(delete(WorkflowStateLink))
        await db.execute(delete(Workflow))

        # Delete globals
        await db.execute(delete(WorkflowState))
        await db.execute(delete(WorkflowAction))
        await db.commit()

        now = datetime.utcnow()

        for label in STATES:
            db.add(
                WorkflowState(
                    label=label,
                    slug=generate_slug(label),
                    color="gray",
                    created_at=now,
                    updated_at=now,
                )
            )

        for label in ACTIONS:
            db.add(
                WorkflowAction(
                    label=label,
                    slug=generate_slug(label),
                    created_at=now,
                    updated_at=now,
                )
            )

        await db.commit()


async def main() -> None:
    await reset_workflow_catalog()
    print("✅ Workflow states/actions reset complete")


if __name__ == "__main__":
    asyncio.run(main())
