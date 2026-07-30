"""
Migration Service
=================
Handles database migration generation and execution using Alembic.
Provides safe migration categorization and rollback capabilities.
"""
import subprocess
import os
from pathlib import Path
from datetime import datetime
from typing import Optional
import re


class MigrationService:
    """Service for managing database migrations."""
    
    def __init__(self):
        self.app_dir = Path(__file__).parent.parent.parent  # infrastructure/metadata/ → app/
        self.backend_dir = self.app_dir.parent
        self.alembic_dir = self.backend_dir / "alembic"
        self.versions_dir = self.alembic_dir / "versions"
    
    def generate_migration(self, message: str, autogenerate: bool = True, auto_upgrade: bool = True) -> dict:
        """Generate a new Alembic migration.
        
        Args:
            message: Migration message/description
            autogenerate: Whether to auto-detect model changes
            auto_upgrade: If True, automatically apply pending migrations first
        """
        try:
            # First check if database is up to date
            if auto_upgrade:
                current_result = self.get_current_revision()
                head_result = self._get_head_revision()
                
                if current_result.get("success") and head_result.get("success"):
                    current = current_result.get("revision", "").strip()
                    head = head_result.get("revision", "").strip()
                    
                    # If not at head, apply pending migrations first
                    if current != head and head:
                        upgrade_result = self.apply_migration("head")
                        if not upgrade_result.get("success"):
                            return {
                                "success": False,
                                "error": f"Failed to apply pending migrations before generating new one: {upgrade_result.get('error')}",
                                "hint": "Apply pending migrations first using the Migrations page"
                            }
            
            cmd = ["alembic", "revision"]
            if autogenerate:
                cmd.append("--autogenerate")
            cmd.extend(["-m", message])
            
            result = subprocess.run(
                cmd,
                cwd=str(self.backend_dir),
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(self.backend_dir)}
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or "Migration generation failed"
                # Provide helpful hint for common errors
                hint = None
                if "Target database is not up to date" in error_msg:
                    hint = "Run 'Apply Migrations' first to sync the database with existing migrations"
                elif "No changes in schema detected" in (result.stdout or ""):
                    return {
                        "success": True,
                        "message": "No schema changes detected - no migration needed",
                        "no_changes": True
                    }
                
                return {
                    "success": False,
                    "error": error_msg,
                    "hint": hint,
                    "stdout": result.stdout
                }
            
            # Check if no changes were detected
            if "No changes in schema detected" in (result.stdout or ""):
                return {
                    "success": True,
                    "message": "No schema changes detected - no migration needed",
                    "no_changes": True
                }
            
            # Extract migration file path from output
            migration_file = self._extract_migration_path(result.stdout)
            
            return {
                "success": True,
                "message": f"Migration generated: {message}",
                "migration_file": migration_file,
                "stdout": result.stdout
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_head_revision(self) -> dict:
        """Get the head revision from migration files."""
        try:
            result = subprocess.run(
                ["alembic", "heads"],
                cwd=str(self.backend_dir),
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(self.backend_dir)}
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr or "Failed to get head revision"
                }
            
            return {
                "success": True,
                "revision": result.stdout.strip().split()[0] if result.stdout.strip() else "",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_migration_path(self, output: str) -> Optional[str]:
        """Extract migration file path from alembic output."""
        # Look for pattern like "Generating /path/to/migration.py"
        match = re.search(r'Generating\s+(.+\.py)', output)
        if match:
            return match.group(1)
        return None
    
    def apply_migration(self, revision: str = "head") -> dict:
        """Apply migrations up to a specific revision."""
        try:
            result = subprocess.run(
                ["alembic", "upgrade", revision],
                cwd=str(self.backend_dir),
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(self.backend_dir)}
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr or "Migration failed",
                    "stdout": result.stdout
                }
            
            return {
                "success": True,
                "message": f"Migrated to {revision}",
                "stdout": result.stdout
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def rollback_migration(self, steps: int = 1) -> dict:
        """Rollback migrations by a number of steps."""
        try:
            result = subprocess.run(
                ["alembic", "downgrade", f"-{steps}"],
                cwd=str(self.backend_dir),
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(self.backend_dir)}
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr or "Rollback failed",
                    "stdout": result.stdout
                }
            
            return {
                "success": True,
                "message": f"Rolled back {steps} migration(s)",
                "stdout": result.stdout
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_current_revision(self) -> dict:
        """Get the current database revision."""
        try:
            result = subprocess.run(
                ["alembic", "current"],
                cwd=str(self.backend_dir),
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(self.backend_dir)}
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr or "Failed to get current revision"
                }
            
            return {
                "success": True,
                "revision": result.stdout.strip(),
                "stdout": result.stdout
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_pending_migrations(self) -> dict:
        """Get list of pending migrations."""
        try:
            result = subprocess.run(
                ["alembic", "history", "--indicate-current"],
                cwd=str(self.backend_dir),
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(self.backend_dir)}
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": result.stderr or "Failed to get migration history"
                }
            
            # Parse history output
            migrations = []
            current_found = False
            
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                
                is_current = "(current)" in line or "(head)" in line
                if is_current:
                    current_found = True
                
                # Extract revision info
                match = re.match(r'([a-f0-9]+)\s*(?:\(current\))?\s*(?:\(head\))?\s*->\s*([a-f0-9]+|None)(?:,\s*(.+))?', line)
                if match:
                    migrations.append({
                        "revision": match.group(1),
                        "parent": match.group(2),
                        "message": match.group(3) or "",
                        "is_current": is_current,
                        "is_pending": not current_found and not is_current
                    })
            
            return {
                "success": True,
                "migrations": migrations,
                "stdout": result.stdout
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def list_migration_files(self) -> list[dict]:
        """List all migration files."""
        if not self.versions_dir.exists():
            return []
        
        migrations = []
        for file in self.versions_dir.glob("*.py"):
            if file.name.startswith("__"):
                continue
            
            stat = file.stat()
            migrations.append({
                "filename": file.name,
                "path": str(file),
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size": stat.st_size
            })
        
        return sorted(migrations, key=lambda x: x["created_at"], reverse=True)
    
    def check_migration_needed(self) -> dict:
        """Check if there are model changes that need migration."""
        try:
            # Use alembic check to see if there are pending changes
            result = subprocess.run(
                ["alembic", "check"],
                cwd=str(self.backend_dir),
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(self.backend_dir)}
            )
            
            # alembic check returns 0 if no changes, 1 if changes needed
            needs_migration = result.returncode != 0
            
            return {
                "success": True,
                "needs_migration": needs_migration,
                "message": result.stdout or result.stderr
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def preview_migration(self) -> dict:
        """Preview what changes would be in the next migration."""
        try:
            # Generate migration to temp file, read it, then delete
            result = subprocess.run(
                ["alembic", "revision", "--autogenerate", "-m", "preview_temp", "--sql"],
                cwd=str(self.backend_dir),
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": str(self.backend_dir)}
            )
            
            return {
                "success": True,
                "preview": result.stdout,
                "stderr": result.stderr
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
