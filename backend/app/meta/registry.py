from typing import Any, Optional
from dataclasses import dataclass, field


@dataclass
class FieldMeta:
    name: str
    label: str
    field_type: str  # string, int, boolean, datetime, link, text
    required: bool = False
    readonly: bool = False
    hidden: bool = False
    unique: bool = False
    link_entity: Optional[str] = None
    child_entity: Optional[str] = None
    parent_entity: Optional[str] = None
    child_parent_fk_field: Optional[str] = None
    query: Optional[dict[str, Any]] = None
    default: Any = None
    search_fields: Optional[list[str]] = None  # Fields to include in search/description for link options
    options: Optional[list[dict[str, Any]]] = None  # Static options for select fields
    nullable: bool = True  # Whether field can be null in database
    in_list_view: bool = False
    # State-based conditions
    show_when: Optional[dict[str, Any]] = None  # e.g., {"workflow_state": ["Rejected"]}
    editable_when: Optional[dict[str, Any]] = None  # e.g., {"workflow_state": ["Draft", "Pending Review"]}
    required_when: Optional[dict[str, Any]] = None  # e.g., {"workflow_state": ["Pending Approval"]}
    # depends_on: field-level display/mandatory conditions based on form data values
    display_depends_on: Optional[str] = None  # e.g., "eval:doc.workflow_state=='draft'"
    mandatory_depends_on: Optional[str] = None  # e.g., "eval:doc.status=='approved'"
    # fetch_from: declarative auto-fill rule — "source_link_field.remote_field_name"
    # e.g., "property.unit_of_measure" means: when `property` changes, fetch property record
    # and copy its `unit_of_measure` value into this field.
    fetch_from: Optional[str] = None
    # filter_by: for query_link fields — the form field whose value is passed as a filter param.
    # e.g., "work_item" means: pass formData.work_item as a filter when loading options.
    # Also informs the UI to show a "(filtered)" badge on this field.
    filter_by: Optional[str] = None
    # column_group: logical group for column visibility in child grids (e.g., "parts", "equipment").
    # Used together with list_view_depends_on on the parent to toggle entire groups.
    column_group: Optional[str] = None
    # list_view_depends_on: controls column visibility in child grids based on parent form data.
    # e.g., "eval:doc.issue_type=='WO Parts Issue'" — column shown only when expression is true.
    list_view_depends_on: Optional[str] = None
    # copy_from_parent: auto-fill this child field from the named parent field on new row.
    # e.g., "site" means: new child row copies parent's site value into this field.
    copy_from_parent: Optional[str] = None
    # readonly_depends_on: conditionally lock a field based on another field's value.
    # e.g., "eval:doc.issue_type=='WO Equipment Issue'" — field becomes readonly when true.
    readonly_depends_on: Optional[str] = None
    # in_options_description: show this field in link dropdown description (independent of in_list_view).
    in_options_description: bool = False
    # placeholder: hint text shown in the empty input.
    placeholder: Optional[str] = None
    # computed_from: reactive formula evaluated on the frontend. Field becomes readonly automatically.
    # e.g., "eval:doc.quantity_issued * doc.unit_cost"
    computed_from: Optional[str] = None
    # link_filter: for child grid link fields — filters scoped to parent field values.
    # e.g., {"work_order_activity": "parent.work_order_activity"}
    link_filter: Optional[dict[str, str]] = None


@dataclass
class NamingMeta:
    """
    Naming configuration for entity IDs.
    
    With the new strategy, the ID IS the naming code (e.g., AST-0001).
    The 'field' attribute is kept for backward compatibility but defaults to 'id'.
    """
    enabled: bool = False
    prefix: str = ""
    digits: int = 4
    field: str = "id"  # Changed from "code" - ID is now the naming field


@dataclass
class ActionMeta:
    """Document action configuration (Frappe-style).
    
    Actions define server-side methods that can be triggered from the frontend.
    The 'method' field is a Python dotted path to the handler function.
    Validation is done inside the handler, NOT by the framework.
    
    Handler signature: async def handler(doc, db, user) -> dict
    """
    action: str  # Action identifier (e.g., "generate_rfq")
    label: str  # Display label (e.g., "Generate RFQ")
    method: str = ""  # Python dotted path (e.g., "app.modules.core.apis.my_entity.handle_action")
    confirm: Optional[str] = None  # Optional confirmation message before execution
    show_when: Optional[dict[str, Any]] = None  # Optional frontend-only UI hint for button visibility


@dataclass
class TabConfig:
    """Tab visibility configuration for related entity tabs."""
    entity: str  # The linked entity name (tab identifier)
    label: Optional[str] = None  # Optional display label override for the tab
    show_when: Optional[dict[str, Any]] = None  # Show tab when conditions met
    hide_when: Optional[dict[str, Any]] = None  # Hide tab when conditions met
    require_data: Optional[str] = None  # Require linked data to exist (e.g., "has_lines")
    display_depends_on: Optional[str] = None  # e.g., "eval:doc.workflow_state=='draft'" (unified depends_on)


@dataclass
class FormStateRules:
    """Form-level state rules controlling editability and child record management."""
    editable_when: Optional[dict[str, list[str]]] = None  # States where form is editable
    can_add_children_when: Optional[dict[str, list[str]]] = None  # States where child records can be added
    tab_rules: list[TabConfig] = field(default_factory=list)  # Tab visibility rules


@dataclass
class AttachmentConfig:
    """Attachment configuration for an entity."""
    allow_attachments: bool = False
    max_attachments: int = 10  # Maximum number of files per record
    allowed_extensions: Optional[list[str]] = None  # e.g., ["pdf", "jpg", "png"], None = all
    max_file_size_mb: int = 10  # Max file size in MB


@dataclass
class WorkflowMeta:
    """Workflow configuration loaded from entity JSON."""
    enabled: bool = False
    show_actions: bool = True
    state_field: str = "workflow_state"
    initial_state: Optional[str] = None
    states: list[str] = field(default_factory=list)
    transitions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ListViewActionMeta:
    """Custom bulk action available in the entity list view."""
    action: str  # Action identifier (e.g., "create_stock_count")
    label: str  # Display label (e.g., "Create Stock Count")
    icon: Optional[str] = None  # Lucide icon name (e.g., "clipboard-list")
    confirm: Optional[str] = None  # Optional confirmation message
    endpoint: Optional[str] = None  # Custom API endpoint path
    method: str = "POST"  # HTTP method


@dataclass
class ChildTableMeta:
    """Inline child table configuration — rendered inside the parent form (not as a tab)."""
    entity: str  # Child entity name (e.g., "purchase_request_line")
    fk_field: str  # FK field on the child pointing to parent (e.g., "purchase_request")
    label: str = ""  # Display label (e.g., "Lines")


@dataclass
class EntityMeta:
    name: str
    label: str
    module: str
    table_name: str
    title_field: str = "name"
    fields: list[FieldMeta] = field(default_factory=list)
    in_sidebar: bool = True
    links: list[dict[str, Any]] = field(default_factory=list)
    children: list[ChildTableMeta] = field(default_factory=list)  # Inline child tables in form
    naming: Optional[NamingMeta] = None
    group: Optional[str] = None
    icon: Optional[str] = None
    search_fields: Optional[list[str]] = None  # Fields for search/description in link options
    actions: list[ActionMeta] = field(default_factory=list)
    form_state: Optional[FormStateRules] = None  # Form-level state management rules
    workflow: Optional[WorkflowMeta] = None  # Workflow config from entity JSON
    attachment_config: Optional[AttachmentConfig] = None  # Attachment settings
    is_tree: bool = False  # Entity supports tree/hierarchical view
    tree_parent_field: Optional[str] = None  # FK field name for tree parent (e.g., "parent_location")
    is_diagram: bool = False  # Entity supports diagram/graph view (e.g., cytoscape)
    is_child_table: bool = False  # Frappe-like: entity is a child table, not standalone
    is_system: bool = False  # Core framework entity editable only in developer mode
    rbac: dict[str, list[str]] = field(default_factory=dict)  # Role to allowed operation mapping
    prefill: Optional[dict[str, Any]] = None  # Pre-fill rules for /new (e.g. {"date_requested": "today"})
    list_view_actions: list[ListViewActionMeta] = field(default_factory=list)  # Custom bulk actions for list view


class MetaRegistry:
    _entities: dict[str, EntityMeta] = {}
    _write_schemas: dict[str, type] = {}
    _read_schemas: dict[str, type] = {}

    @classmethod
    def register(cls, entity: EntityMeta):
        cls._entities[entity.name] = entity

    @classmethod
    def get(cls, name: str) -> Optional[EntityMeta]:
        return cls._entities.get(name)

    @classmethod
    def list_all(cls) -> list[EntityMeta]:
        return list(cls._entities.values())

    @classmethod
    def register_schema(cls, name: str, write: type, read: type) -> None:
        """Store generated Pydantic write/read schemas for *name*."""
        cls._write_schemas[name] = write
        cls._read_schemas[name] = read

    @classmethod
    def get_write_schema(cls, name: str) -> Optional[type]:
        """Return the Pydantic write schema for *name*, or ``None``."""
        return cls._write_schemas.get(name)

    @classmethod
    def get_read_schema(cls, name: str) -> Optional[type]:
        """Return the Pydantic read schema for *name*, or ``None``."""
        return cls._read_schemas.get(name)
    
    @classmethod
    def to_dict(cls, entity: EntityMeta) -> dict:
        """
        Convert EntityMeta to JSON-serializable dict.
        
        Automatically adds system fields (id, created_at, updated_at) to the
        fields list since they are implicit in all entities via BaseModel.
        """
        # Start with user-defined fields
        fields = [
            {
                "name": f.name,
                "label": f.label,
                "field_type": f.field_type,
                "required": f.required,
                "readonly": f.readonly,
                "hidden": f.hidden,
                "unique": f.unique,
                "nullable": f.nullable,
                "link_entity": f.link_entity,
                "child_entity": f.child_entity,
                "parent_entity": f.parent_entity,
                "child_parent_fk_field": f.child_parent_fk_field,
                "query": f.query,
                "default": f.default,
                "options": f.options,
                "in_list_view": f.in_list_view,
                "show_when": f.show_when,
                "editable_when": f.editable_when,
                "required_when": f.required_when,
                "display_depends_on": f.display_depends_on,
                "mandatory_depends_on": f.mandatory_depends_on,
                "fetch_from": f.fetch_from,
                "filter_by": f.filter_by,
                "column_group": f.column_group,
                "list_view_depends_on": f.list_view_depends_on,
                "copy_from_parent": f.copy_from_parent,
                "readonly_depends_on": f.readonly_depends_on,
                "in_options_description": f.in_options_description,
                "placeholder": f.placeholder,
                "computed_from": f.computed_from,
                "link_filter": f.link_filter,
            }
            for f in entity.fields
        ]
        
        # Add implicit system fields at the beginning
        system_fields = [
            {
                "name": "id",
                "label": "ID",
                "field_type": "string",
                "required": False,
                "readonly": True,
                "hidden": True,
                "unique": True,
                "nullable": False,
                "link_entity": None,
                "default": None,
                "options": None,
                "in_list_view": False,
            },
        ]
        
        # Add timestamp fields at the end
        timestamp_fields = [
            {
                "name": "created_at",
                "label": "Created At",
                "field_type": "datetime",
                "required": False,
                "readonly": True,
                "hidden": True,
                "unique": False,
                "nullable": False,
                "link_entity": None,
                "default": None,
                "options": None,
                "in_list_view": False,
            },
            {
                "name": "updated_at",
                "label": "Updated At",
                "field_type": "datetime",
                "required": False,
                "readonly": True,
                "hidden": True,
                "unique": False,
                "nullable": False,
                "link_entity": None,
                "default": None,
                "options": None,
                "in_list_view": False,
            },
        ]
        
        all_fields = system_fields + fields + timestamp_fields
        
        return {
            "name": entity.name,
            "label": entity.label,
            "module": entity.module,
            "group": entity.group,
            "icon": entity.icon,
            "in_sidebar": entity.in_sidebar,
            "is_system": entity.is_system,
            "table_name": entity.table_name,
            "title_field": entity.title_field,
            "search_fields": entity.search_fields or [],
            "fields": all_fields,
            "links": entity.links,
            "children": [cls._child_table_to_dict(c) for c in entity.children] if entity.children else [],
            "naming": cls._naming_to_dict(entity.naming) if entity.naming else None,
            "actions": [cls._action_to_dict(a) for a in entity.actions] if entity.actions else [],
            "form_state": cls._form_state_to_dict(entity.form_state) if entity.form_state else None,
            "attachment_config": cls._attachment_config_to_dict(entity.attachment_config) if entity.attachment_config else None,
            "is_tree": entity.is_tree,
            "tree_parent_field": entity.tree_parent_field,
            "is_diagram": entity.is_diagram,
            "is_child_table": entity.is_child_table,
            "rbac": entity.rbac,
            "list_view_actions": [cls._list_view_action_to_dict(a) for a in entity.list_view_actions] if entity.list_view_actions else [],
        }
    
    @classmethod
    def _naming_to_dict(cls, naming: NamingMeta) -> dict:
        return {
            "enabled": naming.enabled,
            "prefix": naming.prefix,
            "digits": naming.digits,
            "field": naming.field,
        }
    
    @classmethod
    def _action_to_dict(cls, action: ActionMeta) -> dict:
        return {
            "action": action.action,
            "label": action.label,
            "confirm": action.confirm,
            "show_when": action.show_when,
        }

    @classmethod
    def _attachment_config_to_dict(cls, config: 'AttachmentConfig') -> dict:
        return {
            "allow_attachments": config.allow_attachments,
            "max_attachments": config.max_attachments,
            "allowed_extensions": config.allowed_extensions,
            "max_file_size_mb": config.max_file_size_mb,
        }

    @classmethod
    def _child_table_to_dict(cls, child: 'ChildTableMeta') -> dict:
        return {
            "entity": child.entity,
            "fk_field": child.fk_field,
            "label": child.label,
        }

    @classmethod
    def _list_view_action_to_dict(cls, action: 'ListViewActionMeta') -> dict:
        return {
            "action": action.action,
            "label": action.label,
            "icon": action.icon,
            "confirm": action.confirm,
            "endpoint": action.endpoint,
            "method": action.method,
        }

    @classmethod
    def _form_state_to_dict(cls, form_state: 'FormStateRules') -> dict:
        result: dict[str, Any] = {}
        if form_state.editable_when:
            result["editable_when"] = form_state.editable_when
        if form_state.can_add_children_when:
            result["can_add_children_when"] = form_state.can_add_children_when
        if form_state.tab_rules:
            result["tab_rules"] = [
                {
                    "entity": tr.entity,
                    "label": tr.label,
                    "show_when": tr.show_when,
                    "hide_when": tr.hide_when,
                    "require_data": tr.require_data,
                    "display_depends_on": tr.display_depends_on,
                }
                for tr in form_state.tab_rules
            ]
        return result
