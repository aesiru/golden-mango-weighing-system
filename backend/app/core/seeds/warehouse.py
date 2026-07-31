"""
Seed: Warehouse
===============
Idempotent seeds for the weighing-system domain:
Company, CrateClass, and a default Order ready to receive readings.
"""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.seeds import SeedResult
from app.modules.warehouse.models.company import Company
from app.modules.warehouse.models.crate_class import CrateClass
from app.modules.warehouse.models.order import Order


def _short_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


async def seed_company(db: AsyncSession) -> SeedResult:
    """Ensure a default buyer company exists."""
    result = SeedResult(entity="Company")

    existing = await db.execute(
        select(Company).where(Company.email == "buyer@mango-export.com")
    )
    if existing.scalar_one_or_none():
        result.skipped = 1
        return result

    company = Company(
        id=_short_id("COMP"),
        name="Mango Export Co.",
        contact_person="Juan Dela Cruz",
        email="buyer@mango-export.com",
        phone="+63-912-345-6789",
        address="123 Mango Street, Davao City, Philippines",
        status="approved",
    )
    db.add(company)
    await db.flush()
    result.created = 1
    return result


async def seed_crate_classes(db: AsyncSession) -> SeedResult:
    """Ensure standard crate weight classes exist."""
    result = SeedResult(entity="CrateClass")

    classes = [
        ("CC-SMALL",  "Small",   150.0, 250.0),
        ("CC-MEDIUM", "Medium",  250.0, 350.0),
        ("CC-LARGE",  "Large",   350.0, 500.0),
        ("CC-JUMBO",  "Jumbo",   500.0, 800.0),
    ]

    for class_id, name, lo, hi in classes:
        existing = await db.execute(
            select(CrateClass).where(CrateClass.id == class_id)
        )
        if existing.scalar_one_or_none():
            result.skipped += 1
            continue

        db.add(CrateClass(
            id=class_id,
            name=name,
            min_weight=lo,
            max_weight=hi,
        ))
        result.created += 1

    await db.flush()
    return result


async def seed_order(db: AsyncSession) -> SeedResult:
    """Ensure a default pending order exists so the MQTT subscriber
    can route readings immediately without auto-creating one."""
    result = SeedResult(entity="Order")

    existing = await db.execute(
        select(Order).where(Order.status == "pending").limit(1)
    )
    if existing.scalar_one_or_none():
        result.skipped = 1
        return result

    # Find a company and crate class to link
    company_row = await db.execute(select(Company).limit(1))
    company = company_row.scalar_one_or_none()

    class_row = await db.execute(
        select(CrateClass).where(CrateClass.id == "CC-MEDIUM")
    )
    crate_class = class_row.scalar_one_or_none()

    if company is None or crate_class is None:
        result.skipped = 1
        return result

    order = Order(
        id=_short_id("ORD"),
        company=company.id,
        crate_class=crate_class.id,
        total_amount=1000.0,
        current_amount=0.0,
        status="pending",
    )
    db.add(order)
    await db.flush()
    result.created = 1
    return result


async def seed_warehouse(db: AsyncSession):
    """Run all warehouse domain seeds."""
    from app.core.seeds import SeedSummary

    summary = SeedSummary()
    summary.add(await seed_company(db))
    summary.add(await seed_crate_classes(db))
    summary.add(await seed_order(db))
    return summary
