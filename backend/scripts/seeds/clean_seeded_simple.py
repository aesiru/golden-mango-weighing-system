#!/usr/bin/env python3
"""
Clean Seeded Data (Simple)
=========================
Deletes all seeded data in proper order without special privileges.
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.core.database import async_session_maker


async def clean_all_data():
    """Clean all seeded data in reverse dependency order."""
    print("=" * 60)
    print("CLEANING ALL SEEDED DATA")
    print("=" * 60)
    
    async with async_session_maker() as db:
        # Test connection
        result = await db.execute(text("SELECT 1"))
        if not result.scalar():
            print("❌ Database connection failed")
            return
        
        print("\n🗑️  Deleting data in reverse dependency order...")
        
        # Option A scope: business/operational tables seeded from Excel.
        # Excludes auth/roles/users/workflow/module_orders/entity_permissions etc.
        tables_to_clean = [
            # Work Management (transactional)
            'work_order_activity_logs',
            'work_order_checklist_detail',
            'work_order_checklist',
            'work_order_parts_reservation',
            'work_order_parts',
            'work_order_equipment_actual_hours',
            'work_order_equipment_assignment',
            'work_order_equipment',
            'work_order_labor_actual_hours',
            'work_order_labor_assignment',
            'work_order_labor',
            'work_order_activity',
            'work_order',

            # Maintenance Management
            'maintenance_order_detail',
            'maintenance_order',
            'maintenance_trade',
            'maintenance_parts',
            'maintenance_equipment',
            'maintenance_condition',
            'maintenance_interval',
            'maintenance_activity',
            'maintenance_plan',
            'maintenance_request',

            # Purchasing & Stores
            'purchase_return',
            'purchase_receipt',
            'purchase_request_line',
            'purchase_request',
            'request_for_quotation',
            'rfq_line',

            # Inventory transactions
            'putaway',
            'stock_ledger_entry',
            'stock_count_line',
            'stock_count_task',
            'stock_count',
            'transfer_receipt',
            'transfer',
            'inventory_adjustment_line',
            'inventory_adjustment',
            'item_return_line',
            'item_return',
            'item_issue_line',
            'item_issue',

            # Core inventory masters (business)
            'inventory',
            'item',
            'store',

            # Stores setup that commonly references site/location
            'bin',
            'zone',

            # Asset management
            'asset_position',
            'asset_property',
            'asset',
            'position_relation',
            'position',
            'system',
            'location',

            # Other operational
            'disposed',
            'breakdown',
            'inspection',
            'sensor_data',
            'sensor',
            'incident_employee',
            'incident',

            # Maintenance checklists
            'checklist_details',
            'checklist',

            # Supporting masters used by operational tables
            'asset_class_property',
            'asset_class_availability',
            'asset_class',
            'model',
            'manufacturer',
            'vendor',
            'unit_of_measure',
            'item_class',
            'category_of_failure',
            'system_type',
            'location_type',
            'trade',
            'cost_code',
            'department',
            'site',
            'organization',
        ]
        
        deleted_count = 0
        total_records = 0
        
        for table in tables_to_clean:
            # Per-table transactional isolation: if a delete fails, rollback and continue.
            try:
                result = await db.execute(text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema='public' AND table_name = :t)"
                ), {"t": table})
                if not result.scalar():
                    continue

                result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                if not count:
                    print(f"  ⏭️  {table} already empty")
                    continue

                await db.execute(text(f"DELETE FROM {table}"))
                await db.commit()
                print(f"  ✅ Deleted {count:,} records from {table}")
                deleted_count += 1
                total_records += count
            except Exception as e:
                await db.rollback()
                print(f"  ⚠️  Could not clean {table}: {e}")
        
        # Reset sequences for main tables (best-effort; many IDs are strings so sequences often don't exist)
        print("\n🔄 Resetting sequences...")
        sequence_tables = [
            'asset', 'item', 'inventory', 'work_order', 'maintenance_request',
            'purchase_request', 'location', 'system', 'vendor', 'employee',
            'site', 'department', 'organization'
        ]
        
        for table in sequence_tables:
            try:
                # Check if sequence exists
                result = await db.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.sequences 
                        WHERE sequence_name = '{table}_id_seq'
                    );
                """))
                
                if result.scalar():
                    await db.execute(text(f"ALTER SEQUENCE {table}_id_seq RESTART WITH 1"))
                    print(f"  ✅ Reset {table}_id_seq")
            except:
                pass  # Sequence might not exist
        
        print("\n" + "=" * 60)
        print(f"CLEANING COMPLETE!")
        print(f"Tables cleaned: {deleted_count}")
        print(f"Total records deleted: {total_records:,}")
        print("=" * 60)


async def main():
    """Main function."""
    await clean_all_data()


if __name__ == "__main__":
    asyncio.run(main())
