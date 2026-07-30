/**
 * Shared API Types
 * ================
 * All interfaces and types used across domain API composables.
 */

export interface ActionRequest {
  action: "create" | "update" | "delete";
  data?: Record<string, unknown>;
  id?: string;
  children?: Record<string, { rows: any[]; deleted_ids: string[] }>;
}

export interface ActionResponse<T = unknown> {
  status: "success" | "error";
  message: string;
  data?: T;
  errors?: Record<string, string>;
}

export interface ListResponse<T = unknown> {
  status: "success" | "error";
  data: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface FieldMeta {
  name: string;
  label: string;
  field_type: string;
  required?: boolean;
  readonly?: boolean;
  hidden?: boolean;
  unique?: boolean;
  nullable?: boolean;
  in_list_view?: boolean;
  link_entity?: string | null;
  child_entity?: string | null;
  parent_entity?: string | null;
  child_parent_fk_field?: string | null;
  query?: {
    key?: string;
    static_params?: Record<string, unknown>;
    send_form_state?: boolean;
  } | null;
  default?: unknown;
  options?: Array<{ value: string | number; label: string }>;
  show_when?: Record<string, string[]> | null;
  editable_when?: Record<string, string[]> | null;
  required_when?: Record<string, string[]> | null;
  display_depends_on?: string | null;
  mandatory_depends_on?: string | null;
  fetch_from?: string | null;
  filter_by?: string | null;
  column_group?: string | null;
  link_filter?: Record<string, string> | null;
  list_view_depends_on?: string | null;
  copy_from_parent?: string | null;
  readonly_depends_on?: string | null;
  in_options_description?: boolean;
  placeholder?: string | null;
  computed_from?: string | null;
}

export interface TabRule {
  entity: string;
  show_when?: Record<string, string[]> | null;
  hide_when?: Record<string, string[]> | null;
  require_data?: string | null;
  display_depends_on?: string | null;
}

export interface FormStateRules {
  editable_when?: string[] | Record<string, string[]>;
  can_add_children_when?: string[] | Record<string, string[]>;
  tab_rules?: TabRule[];
}

export interface WorkflowAction {
  name: string;
  label: string;
  target: string;
}

export interface WorkflowProgressNextAction {
  action: string;
  label: string;
  target_state: string;
  target_label: string;
  description: string;
}

export interface WorkflowProgressStep {
  key: string;
  title: string;
  description: string;
  status: "completed" | "current" | "upcoming";
  current: boolean;
}

export interface WorkflowProgressNode {
  entity: string;
  record_id: string;
  label: string;
  title: string;
  current_state: string;
  current_state_label: string;
  next_actions: WorkflowProgressNextAction[];
  steps: WorkflowProgressStep[];
  summary?: string | null;
  children: WorkflowProgressNode[];
}

export interface WorkflowProgressResponse {
  entity: string;
  record_id: string;
  title: string;
  summary?: string | null;
  node: WorkflowProgressNode;
}

export interface DocumentAction {
  action: string;
  label: string;
  confirm?: string | null;
  show_when?: Record<string, string[]> | null;
}

export interface ChildTableMeta {
  entity: string;
  fk_field: string;
  label: string;
}

export interface EntityLinkMeta {
  label: string;
  entity: string;
  fk_field: string;
  show_when?: Record<string, string[]> | null;
  hide_when?: Record<string, string[]> | null;
  require_data?: string | null;
  permissions?: {
    can_read: boolean;
    can_create: boolean;
    can_update: boolean;
    can_delete: boolean;
  };
}

export interface NamingMeta {
  enabled: boolean;
  prefix: string;
  digits: number;
  field: string;
}

export interface EntityPermissions {
  can_read: boolean;
  can_create: boolean;
  can_update: boolean;
  can_delete: boolean;
  can_select?: boolean;
  can_export?: boolean;
  can_import?: boolean;
}

export interface LinkFieldPermissions {
  can_read: boolean;
  can_select: boolean;
  can_create: boolean;
}

export interface AttachmentConfig {
  allow_attachments: boolean;
  max_attachments: number;
  allowed_extensions?: string[] | null;
  max_file_size_mb: number;
}

export interface AttachmentItem {
  id: string;
  file_name: string;
  file_size: number;
  mime_type: string | null;
  uploaded_by: string | null;
  description: string | null;
  created_at: string | null;
}

export interface ListViewAction {
  action: string;
  label: string;
  icon?: string | null;
  confirm?: string | null;
  endpoint?: string | null;
  method?: string;
}

export interface EntityMeta {
  name: string;
  label: string;
  module: string;
  table_name: string;
  title_field: string;
  in_sidebar?: boolean;
  fields: FieldMeta[];
  links?: EntityLinkMeta[];
  children?: ChildTableMeta[];
  naming?: NamingMeta | null;
  actions?: DocumentAction[];
  form_state?: FormStateRules | null;
  attachment_config?: AttachmentConfig | null;
  is_tree?: boolean;
  tree_parent_field?: string | null;
  is_diagram?: boolean;
  is_child_table?: boolean;
  list_view_actions?: ListViewAction[];
  workflow: {
    enabled: boolean;
    state_field: string;
    default_state: string;
    states: Record<
      string,
      {
        name: string;
        label: string;
        is_terminal: boolean;
        actions: WorkflowAction[];
      }
    >;
  } | null;
  rbac: Record<string, string[]>;
  permissions?: EntityPermissions;
  link_field_permissions?: Record<string, LinkFieldPermissions>;
}

export interface MetaListItem {
  name: string;
  label: string;
  module: string;
  group?: string | null;
  icon?: string | null;
  in_sidebar: boolean | number;
}

export interface ImportValidationResult {
  valid: boolean;
  errors?: { row: number; errors: { field: string; message: string }[] }[];
  rows?: number;
  warnings?: string[];
}

export interface ImportResult {
  count: number;
  duplicates?: number;
  updated?: number;
  missing?: number;
}

export interface AuditEntry {
  id: number;
  action: string;
  user_id: string | null;
  username: string | null;
  before_snapshot: Record<string, unknown> | null;
  after_snapshot: Record<string, unknown> | null;
  changed_fields: string[] | null;
  created_at: string | null;
}

// Model Editor Types
export interface ModelEditorEntity {
  name: string;
  label: string;
  module: string;
  field_count: number;
  json_path: string;
}

export interface FieldTypeOption {
  value: string;
  label: string;
  description: string;
}

export interface EntityMetadata {
  name: string;
  label: string;
  module: string;
  table_name: string;
  title_field?: string;
  in_sidebar?: number | boolean;
  naming?: string | null;
  icon?: string;
  group?: string;
  search_fields?: string[];
  fields: FieldDefinition[];
  links?: LinkDefinition[];
  children?: ChildDefinition[];
  is_child_table?: boolean;
  actions?: DocumentAction[];
  workflow?: {
    enabled: boolean;
    state_field: string;
    initial_state?: string;
    states?: string[];
    transitions?: Array<{
      from: string;
      to: string;
      action: string;
      label: string;
    }>;
  };
  form_state?: {
    editable_when?: string[];
    can_add_children_when?: string[];
    tab_rules?: Array<{
      entity: string;
      label: string;
      hide_when?: string[];
      require_data?: string;
    }>;
  };
  attachment_config?: {
    allow_attachments: boolean;
    max_attachments: number;
    allowed_extensions?: string[] | null;
    max_file_size_mb: number;
  } | null;
  is_tree?: boolean;
  tree_parent_field?: string | null;
  is_diagram?: boolean;
  rbac?: Record<string, string[]>;
}

export interface FieldDefinition {
  name: string;
  label: string;
  field_type: string;
  required?: boolean;
  readonly?: boolean;
  hidden?: boolean;
  unique?: boolean;
  nullable?: boolean;
  link_entity?: string;
  default?: any;
  in_list_view?: boolean;
  options?: Array<{ value: string; label: string }>;
  child_entity?: string;
  parent_entity?: string;
  child_parent_fk_field?: string;
  query?: {
    key: string;
  };
  show_when?: Record<string, string[]> | null;
  hide_when?: Record<string, string[]> | null;
  display_depends_on?: string | null;
  mandatory_depends_on?: string | null;
  fetch_from?: string | null;
  filter_by?: string | null;
}

export type WorkflowCondition = Record<string, string[]>;

export interface LinkDefinition {
  entity: string;
  fk_field: string;
  label: string;
  show_when?: WorkflowCondition | string[];
  hide_when?: WorkflowCondition | string[];
  require_data?: string;
}

export interface ChildDefinition {
  entity: string;
  fk_field: string;
  label: string;
}

export interface ChangeItem {
  field: string;
  type: "safe" | "dangerous";
  description: string;
}

export interface BackupItem {
  filename: string;
  created_at: string;
  size: number;
}

export interface SyncResultData {
  json_saved: boolean;
  registry_reloaded: boolean;
  model_updated: boolean;
  migration_generated: boolean;
  migration_applied: boolean;
  backup_path?: string | null;
  model_path?: string | null;
  migration_file?: string | null;
  changes: {
    is_safe: boolean;
    items: ChangeItem[];
  };
  warnings: string[];
  errors: string[];
}
