"""
Entity Generator
Handles the creation of new entities and their associated files in the modular structure.
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, List

class EntityGenerator:
    # Tables owned by app/core/framework/models/*.py — never generate entity models for these.
    RESERVED_TABLES = frozenset({
        "users", "roles", "entity_permissions", "user_roles",
        "workflow_states", "workflow_actions", "workflows",
        "workflow_state_links", "workflow_transitions",
        "module_orders", "entity_orders", "attachment", "audit_log",
    })

    # Field type → (python_type, sqlalchemy_column) mapping
    FIELD_TYPE_MAP = {
        "string":            ("str",      "String(255)"),
        "text":              ("str",      "Text"),
        "int":               ("int",      "Integer"),
        "float":             ("float",    "Numeric(10, 2)"),
        "boolean":           ("bool",     "Boolean"),
        "date":              ("datetime", "Date"),
        "datetime":          ("datetime", "DateTime"),
        "select":            ("str",      "String(100)"),
        "attach":            ("str",      "String(500)"),
        "email":             ("str",      "String(255)"),
        "phone":             ("str",      "String(50)"),
        "currency":          ("float",    "Numeric(12, 2)"),
        "percent":           ("float",    "Numeric(5, 2)"),
        "image":             ("str",      "String(500)"),
        "file":              ("str",      "String(500)"),
        "query_link":        ("str",      "String(50)"),
    }

    def __init__(self):
        self.app_dir = Path(__file__).parent.parent
        self.modules_dir = self.app_dir / "modules"

    def _iter_entity_json_paths(self) -> list[Path]:
        paths: list[Path] = []

        core_entities_dir = self.app_dir / "core" / "framework" / "entities"
        if core_entities_dir.exists():
            paths.extend(sorted(core_entities_dir.glob("*.json")))

        if self.modules_dir.exists():
            for module_dir in self.modules_dir.iterdir():
                if not module_dir.is_dir() or module_dir.name.startswith(("_", ".")):
                    continue
                entities_dir = module_dir / "entities"
                if entities_dir.exists():
                    paths.extend(sorted(entities_dir.glob("**/*.json")))

        return paths

    def _resolve_entity_table_name(self, entity_name: str) -> str:
        for json_path in self._iter_entity_json_paths():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            if data.get("name") == entity_name:
                return data.get("table_name", entity_name)

        return entity_name

    def create_entity(self, definition: Dict[str, Any], generate_model: bool = True, overwrite: bool = False) -> Dict[str, Any]:
        name = definition["name"]
        table_name = definition.get("table_name", name)
        if table_name in self.RESERVED_TABLES:
            raise ValueError(f"Table '{table_name}' is reserved by app/core/framework/models - cannot create entity model for it.")
        module = definition.get("module", "core")
        label = definition.get("label", name.replace("_", " ").title())
        naming = definition.get("naming")
        
        module_dir = self.modules_dir / module
        if not module_dir.exists():
            self._create_module_structure(module_dir)
            
        entities_dir = module_dir / "entities"
        models_dir = module_dir / "models"
        
        created_files = {}
        entities_dir.mkdir(parents=True, exist_ok=True)
        json_path = entities_dir / f"{name}.json"
        
        if not json_path.exists() or overwrite:
            entity_json = {
                "name": name,
                "label": label,
                "module": module,
                "table_name": table_name,
                "title_field": definition.get("title_field", "name"),
                "in_sidebar": definition.get("in_sidebar", 1),
                "fields": definition.get("fields", []),
                "rbac": {"SystemManager": ["*"]}
            }
            if naming:
                entity_json["naming"] = naming
                
            with open(json_path, "w") as f:
                json.dump(entity_json, f, indent=2)
            created_files["json"] = str(json_path)

        if generate_model:
            models_dir.mkdir(parents=True, exist_ok=True)
            model_path = models_dir / f"{name}.py"
            if not model_path.exists() or overwrite:
                self._generate_model_file(model_path, definition)
                created_files["model"] = str(model_path)
                self._update_model_init(models_dir, name)

        return {"entity": name, "naming": naming, "files": created_files}

    def _generate_model_file(self, file_path: Path, definition: Dict[str, Any]):
        """Generate the SQLAlchemy model with PK safety."""
        name = definition["name"]
        class_name = "".join(x.title() for x in name.split("_"))
        fields = definition.get("fields", [])
        
        lines = [
            "from datetime import datetime",
            "from sqlalchemy import String, Integer, Boolean, DateTime, Text, ForeignKey, Numeric, Date",
            "from sqlalchemy.orm import Mapped, mapped_column",
            "from app.core.base_model import BaseModel",
            "",
            "",
            f"class {class_name}(BaseModel):",
            f"    \"\"\"{definition.get('label', name)} entity model.\"\"\"",
            f"    __tablename__ = \"{definition.get('table_name', name)}\"",
            ""
        ]
        
        # Skip fields already defined in BaseModel
        skip_fields = ["id", "created_at", "updated_at"]

        for field in fields:
            f_name = field["name"]
            if f_name in skip_fields: continue
            
            f_type = field.get("field_type", "string")
            required = field.get("required", False)
            link_ent = field.get("link_entity")

            if f_type == "link" and link_ent:
                target_table = self._resolve_entity_table_name(link_ent)
                py_type, sa_col = "str", f"String(50), ForeignKey('{target_table}.id')"
            else:
                py_type, sa_col = self.FIELD_TYPE_MAP.get(f_type, ("str", "String(255)"))

            lines.append(f"    {f_name}: Mapped[{py_type}] = mapped_column({sa_col}, nullable={not required}, default=None)")

        if not fields:
            lines.append("    name: Mapped[str] = mapped_column(String(255), nullable=True)")

        with open(file_path, "w") as f:
            f.write("\n".join(lines))

    def _create_module_structure(self, module_dir: Path):
        for sub in ["entities", "models"]:
            (module_dir / sub).mkdir(parents=True, exist_ok=True)
            (module_dir / sub / "__init__.py").touch()
        (module_dir / "__init__.py").touch()

    def _update_model_init(self, models_dir: Path, model_name: str):
        init_file = models_dir / "__init__.py"
        class_name = "".join(x.title() for x in model_name.split("_"))
        line = f"from .{model_name} import {class_name}\n"
        content = []
        if init_file.exists():
            with open(init_file, "r") as f: content = f.readlines()
        if not any(line in l for l in content):
            content.append(line)
            with open(init_file, "w") as f: f.writelines(content)