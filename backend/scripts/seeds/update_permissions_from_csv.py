#!/usr/bin/env python3
"""
Update role permissions from CSV file.
Usage: python backend/update_permissions_from_csv.py
"""
import asyncio
import csv
from pathlib import Path
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker
from app.core.framework.models.auth import Role, EntityPermission

# Permission code mapping
PERMISSION_MAP = {
    'O': 'only_if_creator',
    'Sel': 'select',
    'R': 'read',
    'W': 'write',
    'C': 'create',
    'D': 'delete',
    'Imp': 'import',
    '-': None,  # No permission
}

# Entity name to table name mapping (snake_case)
def entity_to_table(entity_name: str) -> str:
    """Convert entity display name to table name."""
    # Special cases
    special_cases = {
        'PNID Layouts': 'pnid_layout',
        'RFQ Log': 'rfq_log',
        'SensorData': 'sensor_data',
    }
    if entity_name in special_cases:
        return special_cases[entity_name]
    
    # General conversion: replace spaces with underscores, lowercase
    return entity_name.replace(' ', '_').lower()


def parse_permission_string(perm_str: str) -> dict:
    """Parse permission string like 'SelRWCD' into individual permissions."""
    if not perm_str or perm_str == '-':
        return {}
    
    perms = {}
    i = 0
    while i < len(perm_str):
        # Check for multi-char codes
        if i + 2 < len(perm_str) and perm_str[i:i+3] == 'Imp':
            perms['import'] = True
            i += 3
        elif i + 2 < len(perm_str) and perm_str[i:i+3] == 'Sel':
            perms['select'] = True
            i += 3
        elif perm_str[i] == 'O':
            perms['only_if_creator'] = True
            i += 1
        elif perm_str[i] == 'R':
            perms['read'] = True
            i += 1
        elif perm_str[i] == 'W':
            perms['write'] = True
            i += 1
        elif perm_str[i] == 'C':
            perms['create'] = True
            i += 1
        elif perm_str[i] == 'D':
            perms['delete'] = True
            i += 1
        else:
            i += 1
    
    return perms


async def update_permissions(db: AsyncSession):
    """Update permissions from CSV file."""
    csv_path = Path(__file__).parent.parent / "docs/permissions/EAM_Permissions_Simplified csv.csv"
    
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        return
    
    print(f"📄 Reading permissions from: {csv_path}")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    
    if len(rows) < 2:
        print("❌ CSV file is empty or invalid")
        return
    
    # First row is header with role names
    header = rows[0]
    role_names = [r.strip() for r in header[1:]]  # Skip first column (entity name)
    
    print(f"\n📋 Found {len(role_names)} roles:")
    for role in role_names:
        print(f"  - {role}")
    
    # Get role IDs from database
    print("\n� Looking up role IDs...")
    result = await db.execute(select(Role))
    db_roles = {r.name: r.id for r in result.scalars().all()}
    
    role_id_map = {}
    for role_name in role_names:
        if role_name in db_roles:
            role_id_map[role_name] = db_roles[role_name]
            print(f"   ✓ {role_name}: {db_roles[role_name]}")
        else:
            print(f"   ⚠️  Role not found: {role_name}")
    
    # Delete all existing permissions
    print("\n🗑️  Clearing existing permissions...")
    await db.execute(delete(EntityPermission))
    await db.commit()
    print(f"   Cleared all existing permissions")
    
    # Process each entity row
    print("\n📝 Creating new permissions...")
    created_count = 0
    skipped_count = 0
    
    for row_idx, row in enumerate(rows[1:], start=2):
        if not row or len(row) < 2:
            continue
        
        entity_name = row[0].strip()
        if not entity_name:
            continue
        
        entity_table = entity_to_table(entity_name)
        
        # Process each role's permissions for this entity
        for role_idx, role_name in enumerate(role_names):
            if role_idx + 1 >= len(row):
                continue
            
            if role_name not in role_id_map:
                continue
            
            perm_str = row[role_idx + 1].strip()
            
            # Skip if no permissions
            if not perm_str or perm_str == '-':
                continue
            
            # Parse permission string
            perms = parse_permission_string(perm_str)
            
            if not perms:
                continue
            
            # Create permission record
            try:
                perm = EntityPermission(
                    role_id=role_id_map[role_name],
                    entity_name=entity_table,
                    can_select=perms.get('select', False),
                    can_read=perms.get('read', False),
                    can_update=perms.get('write', False),
                    can_create=perms.get('create', False),
                    can_delete=perms.get('delete', False),
                    can_import=perms.get('import', False),
                )
                db.add(perm)
                created_count += 1
                
                if created_count % 50 == 0:
                    print(f"   Created {created_count} permissions...")
                    await db.commit()
                
            except Exception as e:
                print(f"   ⚠️  Row {row_idx}: Failed to create permission for {role_name} on {entity_table}: {e}")
                skipped_count += 1
    
    await db.commit()
    
    print(f"\n✅ Permissions update complete!")
    print(f"   Created: {created_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Total roles: {len(role_names)}")


async def main():
    """Main entry point."""
    print("🚀 Starting permissions update...\n")
    
    async with async_session_maker() as db:
        await update_permissions(db)
    
    print("\n✨ Done!")


if __name__ == "__main__":
    asyncio.run(main())
