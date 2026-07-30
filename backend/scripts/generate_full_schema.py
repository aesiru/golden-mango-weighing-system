#!/usr/bin/env python3
"""Generate full schema dump from local database"""

import asyncio
import sys
from sqlalchemy import text
from app.core.database import async_session_maker

async def generate_schema():
    async with async_session_maker() as db:
        # Get all tables
        result = await db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        
        schema_sql = """-- Full schema dump from local migrated database
-- All tables with String(50) IDs and correct column names
-- Apply with: psql -h host -U user -d database < full_schema.sql

-- Drop all existing tables
"""
        
        # Add DROP statements in reverse dependency order
        drop_order = [
            "asset", "bin", "department", "employee", "item", "location", 
            "manufacturer", "model", "organization", "site", "store", 
            "unit_of_measure", "vendor", "zone", "inventory", "position", 
            "system", "asset_class", "cost_code", "inventory_adjustment", 
            "item_class", "location_type", "workflow_states", "workflow_actions",
            "workflows", "workflow_transitions", "workflow_state_links",
            "users", "roles", "entity_permissions", "user_roles"
        ]
        
        for table in drop_order:
            if table in tables:
                schema_sql += f"DROP TABLE IF EXISTS {table} CASCADE;\n"
        
        schema_sql += "\n-- Create tables\n"
        
        # Generate CREATE TABLE statements
        for table in tables:
            result = await db.execute(text("""
                SELECT column_name, data_type, character_maximum_length, 
                       is_nullable, column_default, ordinal_position
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = :table
                ORDER BY ordinal_position
            """), {"table": table})
            
            columns = result.fetchall()
            schema_sql += f"\nCREATE TABLE {table} (\n"
            
            column_defs = []
            for col in columns:
                col_name, data_type, max_len, is_nullable, default_val, _ = col
                
                # Convert data types
                if data_type == "character varying":
                    data_type = f"VARCHAR({max_len})" if max_len else "VARCHAR"
                elif data_type == "timestamp without time zone":
                    data_type = "TIMESTAMP"
                elif data_type == "timestamp with time zone":
                    data_type = "TIMESTAMPTZ"
                elif data_type == "double precision":
                    data_type = "DOUBLE PRECISION"
                
                col_def = f"    {col_name} {data_type}"
                if is_nullable == "NO":
                    col_def += " NOT NULL"
                if default_val:
                    default_val = default_val.replace("::character varying", "")
                    col_def += f" DEFAULT {default_val}"
                
                column_defs.append(col_def)
            
            schema_sql += ",\n".join(column_defs)
            schema_sql += "\n);\n"
        
        # Add primary keys
        schema_sql += "\n-- Primary Keys\n"
        for table in tables:
            result = await db.execute(text("""
                SELECT column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                  ON kcu.constraint_name = tc.constraint_name
                WHERE tc.table_schema = 'public' 
                  AND tc.table_name = :table
                  AND tc.constraint_type = 'PRIMARY KEY'
                ORDER BY kcu.ordinal_position
            """), {"table": table})
            
            pk_columns = [row[0] for row in result.fetchall()]
            if pk_columns:
                schema_sql += f"ALTER TABLE {table} ADD PRIMARY KEY ({', '.join(pk_columns)});\n"
        
        # Add foreign keys
        schema_sql += "\n-- Foreign Keys\n"
        for table in tables:
            result = await db.execute(text("""
                SELECT tc.constraint_name, kcu.column_name, 
                       ccu.table_name AS ref_table, 
                       ccu.column_name AS ref_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                  ON kcu.constraint_name = tc.constraint_name
                JOIN information_schema.constraint_column_usage ccu 
                  ON ccu.constraint_name = tc.constraint_name
                WHERE tc.table_schema = 'public' 
                  AND tc.table_name = :table
                  AND tc.constraint_type = 'FOREIGN KEY'
                ORDER BY tc.constraint_name, kcu.ordinal_position
            """), {"table": table})
            
            fks = {}
            for row in result.fetchall():
                constraint_name, col_name, ref_table, ref_col = row
                if constraint_name not in fks:
                    fks[constraint_name] = {"cols": [], "ref_table": ref_table, "ref_cols": []}
                fks[constraint_name]["cols"].append(col_name)
                fks[constraint_name]["ref_cols"].append(ref_col)
            
            for constraint_name, fk_info in fks.items():
                cols = ", ".join(fk_info["cols"])
                ref_cols = ", ".join(fk_info["ref_cols"])
                schema_sql += f"ALTER TABLE {table} ADD CONSTRAINT {constraint_name} "
                schema_sql += f"FOREIGN KEY ({cols}) REFERENCES {fk_info['ref_table']} ({ref_cols});\n"
        
        # Write to file
        with open("full_local_schema.sql", "w") as f:
            f.write(schema_sql)
        
        print(f"Schema written to full_local_schema.sql")
        print(f"Total tables: {len(tables)}")
        print(f"Tables: {', '.join(tables)}")

if __name__ == "__main__":
    asyncio.run(generate_schema())
