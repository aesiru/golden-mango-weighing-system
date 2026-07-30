"""
Seed: Workflows
===============
Creates entity-specific workflow configurations linking states and transitions.
Requires workflow states and actions to already exist (run those seeders first).
Idempotent — skips workflows whose target_entity already exists.

All module entities removed - only core framework workflows will be created
Future modules can add their own workflows using the same pattern.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.seeds import SeedResult


async def seed_workflows(db: AsyncSession) -> SeedResult:
    result = SeedResult(entity="Workflow")

    # All module-specific workflows removed - only core framework remains
    # Future modules can add their own workflows using the same pattern
    print("  ⚠️  Skipping module workflows - all business modules removed")
    result.skipped = 1  # Mark as skipped since no module workflows to create

    return result
