"""
Model Generator Service
=======================
Generates and updates SQLAlchemy model files from entity metadata.
Handles field type mappings, imports, and relationships.
"""
import json
import re
from pathlib import Path
from typing import Any, Optional
from datetime import datetime


class ModelGeneratorService:
    """Service for generating SQLAlchemy models from metadata."""

    # Avoid SQLAlchemy class registry collisions with app/core/framework/models/*.py classes.
    CLASS_NAME_OVERRIDES = {
        "workflow_state": "EntityWorkflowState",
        "workflow_action": "EntityWorkflowAction",
    }

    # Tables already owned by app/core/framework/models/*.py — never generate entity models for these.
    RESERVED_TABLES = frozenset({
        "users", "roles", "entity_permissions", "user_roles",
        "workflow_states", "workflow_actions", "workflows",
        "workflow_state_links", "workflow_transitions",
        "module_orders", "entity_orders", "attachment", "audit_log",
    })

    # Fields inherited from BaseModel — skip them in generated code.
    BASEMODEL_FIELDS = frozenset({"id", "created_at", "updated_at"})

    # SQLAlchemy type mappings
    TYPE_MAPPINGS = {
        "string": {"py_type": "str", "sa_type": "String(255)", "imports": ["String"]},
        "text": {"py_type": "str", "sa_type": "Text", "imports": ["Text"]},
        "int": {"py_type": "int", "sa_type": "Integer", "imports": ["Integer"]},
        "float": {"py_type": "float", "sa_type": "Float", "imports": ["Float"]},
        "boolean": {"py_type": "bool", "sa_type": "Boolean", "imports": ["Boolean"]},
        "date": {"py_type": "date", "sa_type": "Date", "imports": ["Date"]},
        "datetime": {"py_type": "datetime", "sa_type": "DateTime", "imports": ["DateTime"]},
        "link": {"py_type": "str", "sa_type": "String(50)", "imports": ["String", "ForeignKey"]},
        "select": {"py_type": "str", "sa_type": "String(100)", "imports": ["String"]},
        "attach": {"py_type": "str", "sa_type": "String(500)", "imports": ["String"]},
        "image": {"py_type": "str", "sa_type": "String(500)", "imports": ["String"]},
        "file": {"py_type": "str", "sa_type": "String(500)", "imports": ["String"]},
        "attach_image": {"py_type": "str", "sa_type": "String(500)", "imports": ["String"]},
        "parent_child_link": {"py_type": "str", "sa_type": "String(50)", "imports": ["String", "ForeignKey"]},
        "query_link": {"py_type": "str", "sa_type": "String(50)", "imports": ["String"]},
    }

    _ENTITY_TABLE_MAP: dict[str, str] | None = None
    _TABLE_ENTITY_MAP: dict[str, str] | None = None
    
    def __init__(self):
        self.app_dir = Path(__file__).parent.parent.parent  # infrastructure/metadata/ → app/
        self.modules_dir = self.app_dir / "modules"
    
    # Map display module names (from entity JSON) to actual filesystem directory names.
    MODULE_DIR_MAP: dict[str, str] = {}

    def _resolve_module_dir(self, module_display: str) -> str:
        """Resolve a module display name to the actual filesystem directory name.

        Strategy:
        1. If it already matches an existing directory, use it as-is.
        2. Check the MODULE_DIR_MAP cache.
        3. Scan modules/ for dirs that contain entities/ and build a reverse
           map from each entity JSON's "module" field to the dir name.
        4. Fall back to slugifying the display name.
        """
        # Direct match (e.g. "core" passed directly)
        if (self.modules_dir / module_display).is_dir():
            return module_display

        # Cached
        if module_display in self.MODULE_DIR_MAP:
            return self.MODULE_DIR_MAP[module_display]

        # Build map by scanning entity JSONs
        import json as _json
        for d in self.modules_dir.iterdir():
            if not d.is_dir() or d.name.startswith(("_", ".")):
                continue
            edir = d / "entities"
            if not edir.exists():
                continue
            for jp in edir.glob("*.json"):
                try:
                    mod_name = _json.loads(jp.read_text(encoding="utf-8")).get("module")
                    if mod_name:
                        self.MODULE_DIR_MAP[mod_name] = d.name
                except Exception:
                    pass

        if module_display in self.MODULE_DIR_MAP:
            return self.MODULE_DIR_MAP[module_display]

        slug = re.sub(r"[^a-zA-Z0-9]+", "_", module_display).strip("_").lower()
        return slug

    def get_model_path(self, entity_name: str, module: str, *, json_path: Optional[Path] = None) -> Path:
        """Get the model file path for an entity.

        If *json_path* is provided the module directory is derived directly from
        the JSON file's location (json_path.parent.parent == module dir).
        Otherwise the *module* display name is resolved via _resolve_module_dir.
        """
        if json_path is not None:
            # json_path lives at  modules/<mod_dir>/entities/<name>.json
            module_dir = json_path.parent.parent
            return module_dir / "models" / f"{entity_name}.py"
        resolved = self._resolve_module_dir(module)
        return self.modules_dir / resolved / "models" / f"{entity_name}.py"

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

    def _ensure_entity_table_maps(self):
        if self._ENTITY_TABLE_MAP is not None and self._TABLE_ENTITY_MAP is not None:
            return

        entity_to_table: dict[str, str] = {}
        table_to_entity: dict[str, str] = {}

        for json_path in self._iter_entity_json_paths():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            entity_name = data.get("name")
            if not entity_name:
                continue

            table_name = data.get("table_name", entity_name)
            entity_to_table[entity_name] = table_name
            table_to_entity[table_name] = entity_name

        self._ENTITY_TABLE_MAP = entity_to_table
        self._TABLE_ENTITY_MAP = table_to_entity

    def _resolve_entity_table_name(self, entity_name: str) -> str:
        self._ensure_entity_table_maps()
        assert self._ENTITY_TABLE_MAP is not None
        return self._ENTITY_TABLE_MAP.get(entity_name, entity_name)

    def _resolve_table_entity_name(self, table_name: str) -> str:
        self._ensure_entity_table_maps()
        assert self._TABLE_ENTITY_MAP is not None
        return self._TABLE_ENTITY_MAP.get(table_name, table_name)
    
    def generate_model_code(self, metadata: dict) -> str:
        """Generate SQLAlchemy model code from metadata."""
        name = metadata["name"]
        label = metadata.get("label", name.replace("_", " ").title())
        table_name = metadata.get("table_name", name)
        fields = metadata.get("fields", [])
        
        # Collect required imports
        imports = set(["String"])  # Always need String for base
        datetime_imports = set()
        
        for field in fields:
            field_type = field.get("field_type", "string")
            mapping = self.TYPE_MAPPINGS.get(field_type, self.TYPE_MAPPINGS["string"])
            imports.update(mapping["imports"])
            
            if field_type == "date":
                datetime_imports.add("date")
            elif field_type == "datetime":
                datetime_imports.add("datetime")
        
        # Build import statements
        lines = []
        
        # Datetime imports
        if datetime_imports:
            lines.append(f"from datetime import {', '.join(sorted(datetime_imports))}")
        
        # SQLAlchemy imports
        sa_imports = sorted(imports)
        lines.append(f"from sqlalchemy import {', '.join(sa_imports)}")
        lines.append("from sqlalchemy.orm import Mapped, mapped_column")
        lines.append("from app.core.base_model import BaseModel")
        lines.append("")
        lines.append("")
        
        # Class definition
        class_name = self._to_class_name(name)
        lines.append(f"class {class_name}(BaseModel):")
        lines.append(f'    """{label} entity model."""')
        lines.append(f'    __tablename__ = "{table_name}"')
        lines.append("    ")
        
        # Generate fields (skip those inherited from BaseModel)
        for field in fields:
            if field.get("name") in self.BASEMODEL_FIELDS:
                continue
            field_line = self._generate_field_line(field)
            if field_line:
                lines.append(f"    {field_line}")
        
        lines.append("")
        
        return "\n".join(lines)
    
    def _generate_field_line(self, field: dict) -> Optional[str]:
        """Generate a single field definition line."""
        name = field.get("name")
        if not name:
            return None
        
        field_type = field.get("field_type", "string")
        required = field.get("required", False)
        nullable = field.get("nullable", True)
        link_entity = field.get("link_entity")
        child_entity = field.get("child_entity")
        default = field.get("default")
        unique = field.get("unique", False)
        
        mapping = self.TYPE_MAPPINGS.get(field_type, self.TYPE_MAPPINGS["string"])
        py_type = mapping["py_type"]
        sa_type = mapping["sa_type"]
        
        # Build column arguments
        col_args = [sa_type]
        
        # Add ForeignKey for link fields
        if field_type == "link" and link_entity:
            target_table = self._resolve_entity_table_name(link_entity)
            col_args.append(f'ForeignKey("{target_table}.id")')
        
        # Add ForeignKey for parent_child_link (uses child_entity)
        if field_type == "parent_child_link" and child_entity:
            target_table = self._resolve_entity_table_name(child_entity)
            col_args.append(f'ForeignKey("{target_table}.id")')
        
        # Nullable - use explicit nullable field or derive from required
        col_args.append(f"nullable={nullable}")
        
        # Unique
        if unique:
            col_args.append("unique=True")
        
        # Default value
        if default is not None:
            if isinstance(default, str):
                col_args.append(f'default="{default}"')
            elif isinstance(default, bool):
                col_args.append(f"default={default}")
            else:
                col_args.append(f"default={default}")
        elif nullable:
            col_args.append("default=None")
        
        return f"{name}: Mapped[{py_type}] = mapped_column({', '.join(col_args)})"
    
    def _to_class_name(self, name: str) -> str:
        """Convert snake_case to PascalCase."""
        if name in self.CLASS_NAME_OVERRIDES:
            return self.CLASS_NAME_OVERRIDES[name]
        return "".join(word.title() for word in name.split("_"))
    
    def update_model_file(self, metadata: dict, backup: bool = True, *, json_path: Optional[Path] = None) -> dict:
        """Update or create the model file for an entity.

        *json_path*: if provided, the model is written next to the JSON's
        module directory (avoids relying on metadata["module"] display name).
        """
        name = metadata["name"]
        table_name = metadata.get("table_name", name)
        if table_name in self.RESERVED_TABLES:
            return {"success": False, "error": f"Table '{table_name}' is reserved by app/core/framework/models — skipping", "skipped": True}
        module = metadata.get("module", "core")
        model_path = self.get_model_path(name, module, json_path=json_path)
        
        # Ensure models directory exists
        model_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate new model code
        model_code = self.generate_model_code(metadata)
        
        # Skip write if code is unchanged (avoids triggering uvicorn reload)
        if model_path.exists():
            current_code = model_path.read_text()
            if self._normalize_code(current_code) == self._normalize_code(model_code):
                return {
                    "success": True,
                    "model_path": str(model_path),
                    "backup_path": None,
                    "class_name": self._to_class_name(name),
                    "skipped": True,
                }
        
        # Backup existing file
        backup_path = None
        if backup and model_path.exists():
            backup_dir = self.app_dir.parent / "backups" / "models"
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{name}_{timestamp}.py"
            
            with open(model_path, 'r') as f:
                content = f.read()
            with open(backup_path, 'w') as f:
                f.write(content)
        
        # Write model file
        with open(model_path, 'w') as f:
            f.write(model_code)
        
        # Update __init__.py
        self._update_model_init(model_path.parent, name)
        
        return {
            "success": True,
            "model_path": str(model_path),
            "backup_path": str(backup_path) if backup_path else None,
            "class_name": self._to_class_name(name)
        }
    
    def _update_model_init(self, models_dir: Path, model_name: str):
        """Update __init__.py to export the model."""
        init_file = models_dir / "__init__.py"
        class_name = self._to_class_name(model_name)
        import_line = f"from .{model_name} import {class_name}"
        
        content = []
        if init_file.exists():
            with open(init_file, 'r') as f:
                content = f.readlines()
        
        # Check if import already exists
        if any(import_line in line for line in content):
            return
        
        # Add import
        content.append(f"{import_line}\n")
        
        with open(init_file, 'w') as f:
            f.writelines(content)
    
    def get_model_diff(self, metadata: dict, *, json_path: Optional[Path] = None) -> dict:
        """Get the diff between current model and what would be generated."""
        name = metadata["name"]
        module = metadata.get("module", "core")
        model_path = self.get_model_path(name, module, json_path=json_path)
        
        new_code = self.generate_model_code(metadata)
        
        if not model_path.exists():
            return {
                "exists": False,
                "new_code": new_code,
                "current_code": None,
                "has_changes": True
            }
        
        with open(model_path, 'r') as f:
            current_code = f.read()
        
        # Normalize for comparison (strip whitespace differences)
        current_normalized = self._normalize_code(current_code)
        new_normalized = self._normalize_code(new_code)
        
        return {
            "exists": True,
            "new_code": new_code,
            "current_code": current_code,
            "has_changes": current_normalized != new_normalized
        }
    
    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison."""
        # Remove extra whitespace and blank lines
        lines = [line.rstrip() for line in code.split('\n')]
        lines = [line for line in lines if line.strip()]
        return '\n'.join(lines)
    
    def extract_fields_from_model(self, model_path: Path) -> list[dict]:
        """Extract field definitions from an existing model file."""
        if not model_path.exists():
            return []
        
        with open(model_path, 'r') as f:
            content = f.read()
        
        fields = []
        # Match field definitions like: field_name: Mapped[type] = mapped_column(...)
        pattern = r'(\w+):\s*Mapped\[(\w+)\]\s*=\s*mapped_column\(([^)]+)\)'
        
        for match in re.finditer(pattern, content):
            field_name = match.group(1)
            py_type = match.group(2)
            col_args = match.group(3)
            
            # Skip system fields
            if field_name in ['id', 'created_at', 'updated_at']:
                continue
            
            field = {
                "name": field_name,
                "field_type": self._infer_field_type(py_type, col_args),
                "required": "nullable=False" in col_args or "nullable=True" not in col_args,
            }
            
            # Check for ForeignKey
            fk_match = re.search(r'ForeignKey\(["\']([\w_]+)\.id["\']\)', col_args)
            if fk_match:
                field["field_type"] = "link"
                field["link_entity"] = self._resolve_table_entity_name(fk_match.group(1))
            
            # Check for unique
            if "unique=True" in col_args:
                field["unique"] = True
            
            fields.append(field)
        
        return fields
    
    def _infer_field_type(self, py_type: str, col_args: str) -> str:
        """Infer field type from Python type and column arguments."""
        if "Text" in col_args:
            return "text"
        if py_type == "int":
            return "int"
        if py_type == "float":
            return "float"
        if py_type == "bool":
            return "boolean"
        if py_type == "date":
            return "date"
        if py_type == "datetime":
            return "datetime"
        if "ForeignKey" in col_args:
            return "link"
        return "string"
