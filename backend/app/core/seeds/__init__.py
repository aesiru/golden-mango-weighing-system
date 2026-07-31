"""
Seed Package
============
Modular, idempotent database seeders organized by domain.

Each seeder returns a SeedResult with created/skipped counts.
Call run_all_seeds() to run the full pipeline in dependency order.
"""
from dataclasses import dataclass, field
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class SeedResult:
    entity: str
    created: int = 0
    skipped: int = 0
    updated: int = 0

    def __repr__(self) -> str:
        return f"<SeedResult {self.entity}: +{self.created} ={self.skipped} ~{self.updated}>"


@dataclass
class SeedSummary:
    results: List[SeedResult] = field(default_factory=list)

    def add(self, result: SeedResult) -> None:
        self.results.append(result)

    @property
    def total_created(self) -> int:
        return sum(r.created for r in self.results)

    @property
    def total_skipped(self) -> int:
        return sum(r.skipped for r in self.results)

    def print_report(self) -> None:
        print("\n📊 Seed Summary")
        print("─" * 50)
        for r in self.results:
            symbol = "✅" if r.created > 0 else "⏭️ "
            print(f"  {symbol}  {r.entity:<30} +{r.created:>3} created  ={r.skipped:>3} skipped")
        print("─" * 50)
        print(f"  Total: +{self.total_created} created, ={self.total_skipped} skipped")
        print()


async def run_all_seeds(db: AsyncSession) -> SeedSummary:
    """
    Run all domain seeders in dependency order.
    Safe to call multiple times — all seeders are idempotent.
    """
    from app.core.seeds.roles import seed_roles
    from app.core.seeds.permissions import seed_entity_permissions
    from app.core.seeds.workflow_states import seed_workflow_states
    from app.core.seeds.workflow_actions import seed_workflow_actions
    from app.core.seeds.workflows import seed_workflows
    from app.core.seeds.warehouse import seed_warehouse
    summary = SeedSummary()

    print("🌱 Running seed pipeline...")

    # 1. Core auth — roles before permissions
    summary.add(await seed_roles(db))
    summary.add(await seed_entity_permissions(db))

    # 2. Workflow catalog — states/actions before workflows
    summary.add(await seed_workflow_states(db))
    summary.add(await seed_workflow_actions(db))
    summary.add(await seed_workflows(db))

    # 3. Warehouse domain — company, crate classes, default order
    wh_summary = await seed_warehouse(db)
    summary.results.extend(wh_summary.results)

    summary.print_report()
    return summary
