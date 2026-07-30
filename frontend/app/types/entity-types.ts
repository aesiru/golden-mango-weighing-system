// Auto-generated TypeScript types from entity metadata
// Do not edit manually - run: python -m app.forge generate-types

export interface BaseEntity {
  id: string
  created_at: string
  updated_at: string
}

export interface Attachment extends BaseEntity {
  entity_name: string
  record_id: string
  file_name: string
  original_name: string
  file_path: string
  file_size: number
  mime_type?: string
  uploaded_by?: string
  description?: string
}

export interface AuditLog extends BaseEntity {
  entity_name: string
  record_id: string
  action: string
  user_id?: string
  username?: string
  before_snapshot?: string
  after_snapshot?: string
  changed_fields?: string
}

export interface Company extends BaseEntity {
  name: string
  contact_person?: string
  email: string
  phone?: string
  address?: string
  registration_date?: string
  status?: string
  user?: string
}

export interface Crate extends BaseEntity {
  code: string
  order: string
  crate_class: string
  target?: number
  counted?: number
}

export interface CrateClass extends BaseEntity {
  name?: string
  min_weight?: number
  max_weight?: number
}

export interface EmailLog extends BaseEntity {
  subject?: string
  recipients?: string
  cc?: string
  bcc?: string
  from_address?: string
  entity_name?: string
  record_id?: string
  event_type?: string
  status?: string
  error_message?: string
  html_body?: string
  sent_at?: string
  sent_by?: string
}

export interface EntityOrder extends BaseEntity {
  entity_name: string
  module_name: string
  sort_order: number
}

export interface EntityPermission extends BaseEntity {
  role: string
  entity_name: string
  can_read: boolean
  can_create: boolean
  can_update: boolean
  can_delete: boolean
  can_select: boolean
  can_export: boolean
  can_import: boolean
  in_sidebar: boolean
}

export interface ErrorLog extends BaseEntity {
  status?: number
  title?: string
  message?: string
}

export interface ModuleOrder extends BaseEntity {
  module_name: string
  sort_order: number
}

export interface NotificationSubscription extends BaseEntity {
  user_id?: string
  entity_type?: string
  entity_id?: string
  event?: string
  recipient_email?: string
  is_active?: boolean
}

export interface Order extends BaseEntity {
  company: string
  crate_class: string
  total_amount?: number
  current_amount?: number
  status?: string
}

export interface Reading extends BaseEntity {
  crate: string
  order: string
  weight_grams: number
  recorded_at: string
  valid?: boolean
}

export interface Role extends BaseEntity {
  name: string
  description?: string
  is_active: boolean
}

export interface ScheduledJobLog extends BaseEntity {
  job_id: string
  job_name: string
  status: string
  started_at: string
  completed_at?: string
  duration_seconds?: number
  records_created?: number
  records_updated?: number
  error_message?: string
  error_traceback?: string
  details?: string
  trigger_type?: string
  cron_expression?: string
}

export interface User extends BaseEntity {
  username?: string
  email: string
  full_name: string
  first_name?: string
  last_name?: string
  contact_number?: string
  department?: string
  site?: string
  employee_id?: string
  is_active: boolean
  is_superuser?: boolean
}

export interface UserActivity extends BaseEntity {
  user_id: string
  username: string
  activity_type: string
  entity_name?: string
  page_path?: string
  page_label?: string
  visit_count: number
  score: number
  last_visited_at: string
}

export interface Workflow extends BaseEntity {
  name: string
  target_entity: string
  is_active: boolean
}

export interface WorkflowAction extends BaseEntity {
  label: string
  slug?: string
}

export interface WorkflowState extends BaseEntity {
  label: string
  slug?: string
  color?: string
}

export interface WorkflowStateLink extends BaseEntity {
  workflow_id: string
  state_id: string
  is_initial: boolean
  sort_order: number
}

export interface WorkflowTransition extends BaseEntity {
  workflow_id: string
  from_state_id: string
  action_id: string
  to_state_id: string
  allowed_roles?: string
  sort_order: number
}
