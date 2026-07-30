"""
Infrastructure Layer: Metadata Reader

Reads entity metadata from JSON files on disk.

Clean Architecture Layer: Infrastructure
Responsibility: Read entity metadata from file system
"""
import json
from pathlib import Path
from typing import Any, Optional


class JsonMetadataReader:
    """Reads entity metadata from JSON files on disk."""

    def __init__(self):
        self._app_dir = Path(__file__).parent.parent.parent
        self._modules_dir = self._app_dir / "modules"
        self._core_framework_entities_dir = self._app_dir / "core" / "framework" / "entities"

    @staticmethod
    def _iter_json_files(entities_dir: Path):
        for item in entities_dir.iterdir():
            if item.name.startswith("_"):
                continue

            if item.is_file() and item.suffix == ".json":
                yield item
                continue

            if item.is_dir():
                nested_json = item / f"{item.name}.json"
                if nested_json.exists():
                    yield nested_json

    def _iter_entity_roots(self):
        if self._core_framework_entities_dir.exists():
            yield "core", self._core_framework_entities_dir

        for module_dir in self._modules_dir.iterdir():
            if not module_dir.is_dir() or module_dir.name.startswith("_"):
                continue

            entities_dir = module_dir / "entities"
            if entities_dir.exists():
                yield module_dir.name, entities_dir

    def list_all_entities(self) -> list[dict]:
        entities = []
        for module_name, entities_dir in self._iter_entity_roots():
            for json_file in self._iter_json_files(entities_dir):
                try:
                    with open(json_file, "r") as f:
                        data = json.load(f)
                    entities.append({
                        "name": data.get("name", json_file.stem),
                        "label": data.get("label", json_file.stem),
                        "module": data.get("module", module_name),
                        "field_count": len(data.get("fields", [])),
                        "json_path": str(json_file),
                    })
                except Exception as e:
                    print(f"Error reading {json_file}: {e}")
        return sorted(entities, key=lambda x: (x["module"], x["name"]))

    def get_entity_metadata(self, entity_name: str) -> Optional[dict]:
        json_path = self.get_entity_json_path(entity_name)
        if not json_path:
            return None
        with open(json_path, "r") as f:
            return json.load(f)

    def get_entity_json_path(self, entity_name: str) -> Optional[Path]:
        for _, entities_dir in self._iter_entity_roots():
            flat_path = entities_dir / f"{entity_name}.json"
            if flat_path.exists():
                return flat_path
            nested_path = entities_dir / entity_name / f"{entity_name}.json"
            if nested_path.exists():
                return nested_path
        return None
