"""
Infrastructure Layer: Metadata Writer

Writes entity metadata to JSON files and manages backups.

Clean Architecture Layer: Infrastructure
Responsibility: Write entity metadata to file system
"""
import json
from pathlib import Path
from typing import Any, Optional


class JsonMetadataWriter:
    """Writes entity metadata to JSON files and manages backups."""

    def __init__(self, reader: "JsonMetadataReader"):
        self._reader = reader
        self._app_dir = Path(__file__).parent.parent.parent
        self._backup_dir = self._app_dir.parent / "backups" / "metadata"

    def _resolve_target_path(self, entity_name: str, metadata: dict) -> Path:
        existing_path = self._reader.get_entity_json_path(entity_name)
        if existing_path:
            return existing_path

        module_name = str(metadata.get("module", "")).strip().lower()
        is_system = bool(metadata.get("is_system", False)) or module_name == "core"

        if is_system:
            target_dir = self._reader._core_framework_entities_dir
        elif module_name:
            target_dir = self._app_dir / "modules" / module_name / "entities"
        else:
            raise FileNotFoundError(f"Entity '{entity_name}' JSON not found and no target module provided")

        target_dir.mkdir(parents=True, exist_ok=True)
        return target_dir / f"{entity_name}.json"

    def save_metadata(self, entity_name: str, metadata: dict) -> str:
        json_path = self._resolve_target_path(entity_name, metadata)
        with open(json_path, "w") as f:
            json.dump(metadata, f, indent=2)
        return str(json_path)

    def create_backup(self, entity_name: str) -> Optional[str]:
        json_path = self._reader.get_entity_json_path(entity_name)
        if not json_path:
            return None
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        import shutil
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self._backup_dir / f"{entity_name}_{timestamp}.json"
        shutil.copy2(json_path, backup_path)
        return str(backup_path)

    def list_backups(self, entity_name: str) -> list[dict]:
        if not self._backup_dir.exists():
            return []
        from datetime import datetime
        backups = []
        for backup_file in self._backup_dir.glob(f"{entity_name}_*.json"):
            stat = backup_file.stat()
            backups.append({
                "filename": backup_file.name,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "size": stat.st_size,
            })
        return sorted(backups, key=lambda x: x["created_at"], reverse=True)

    def restore_backup(self, entity_name: str, backup_filename: str) -> dict:
        backup_path = self._backup_dir / backup_filename
        if not backup_path.exists():
            return {"success": False, "error": "Backup not found"}
        json_path = self._reader.get_entity_json_path(entity_name)
        if not json_path:
            return {"success": False, "error": f"Entity '{entity_name}' not found"}
        import shutil
        shutil.copy2(backup_path, json_path)
        return {"success": True, "restored_from": str(backup_path)}
