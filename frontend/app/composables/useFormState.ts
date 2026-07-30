/**
 * Form State Management Composable
 * 
 * Resolves field visibility, editability, tab visibility, and action availability
 * based on workflow state and form data conditions defined in entity metadata.
 */
import type { FieldMeta, EntityMeta, FormStateRules, TabRule } from '~/composables/useApiTypes'

/**
 * Check if form data matches a condition.
 * Condition format: { "field_name": ["allowed_value_1", "allowed_value_2"] }
 * All conditions must match (AND logic).
 */
/**
 * Evaluate a depends_on expression against form data.
 * Supports formats:
 *   - "eval:doc.field_name=='value'"  (eval expression)
 *   - "eval:doc.field_name"  (truthy check)
 *   - "eval:doc.field_name!='value'"  (not equal)
 *   - "eval:doc.field_name in ['a','b']"  (in list - simplified)
 *   - "field_name"  (simple truthy check on field)
 */
export function evaluateDependsOn(
  expression: string | null | undefined,
  formData: Record<string, any>
): boolean {
  if (!expression) return true

  let expr = expression.trim()

  // Handle eval: prefix
  if (expr.startsWith('eval:')) {
    expr = expr.slice(5).trim()
  }

  // Replace doc.xxx with actual form data values
  // Build a safe evaluation context
  try {
    // Create a proxy "doc" object from formData
    const doc = { ...formData }

    // Simple expression patterns we support safely:
    // 1. doc.field == 'value' or doc.field === 'value'
    // 2. doc.field != 'value' or doc.field !== 'value'
    // 3. doc.field (truthy)
    // 4. !doc.field (falsy)

    // Pattern: doc.field_name == 'value' or doc.field_name === 'value'
    const eqMatch = expr.match(/^doc\.([\w]+)\s*={2,3}\s*['"]([^'"]*)['"]$/)
    if (eqMatch) {
      const [, field, value] = eqMatch
      return String(doc[field!] ?? '') === value
    }

    // Pattern: doc.field_name != 'value' or doc.field_name !== 'value'
    const neqMatch = expr.match(/^doc\.([\w]+)\s*!={1,2}\s*['"]([^'"]*)['"]$/)
    if (neqMatch) {
      const [, field, value] = neqMatch
      return String(doc[field!] ?? '') !== value
    }

    // Pattern: doc.field_name in ['value1', 'value2'] (in list check)
    const inMatch = expr.match(/^doc\.([\w]+)\s+in\s+\[([^\]]+)\]$/)
    if (inMatch) {
      const [, field, rawList] = inMatch
      const values = rawList!.split(',').map(v => v.trim().replace(/^['"]|['"]$/g, ''))
      return values.includes(String(doc[field!] ?? ''))
    }

    // Pattern: doc.field_name not in ['value1', 'value2'] (not in list check)
    const notInMatch = expr.match(/^doc\.([\w]+)\s+not\s+in\s+\[([^\]]+)\]$/)
    if (notInMatch) {
      const [, field, rawList] = notInMatch
      const values = rawList!.split(',').map(v => v.trim().replace(/^['"]|['"]$/g, ''))
      return !values.includes(String(doc[field!] ?? ''))
    }

    // Pattern: !doc.field_name (falsy check)
    const falsyMatch = expr.match(/^!doc\.([\w]+)$/)
    if (falsyMatch) {
      const [, field] = falsyMatch
      return !doc[field!]
    }

    // Pattern: doc.field_name (truthy check)
    const truthyMatch = expr.match(/^doc\.([\w]+)$/)
    if (truthyMatch) {
      const [, field] = truthyMatch
      return !!doc[field!]
    }

    // Pattern: simple field name (truthy check)
    const simpleMatch = expr.match(/^([\w]+)$/)
    if (simpleMatch) {
      const [, field] = simpleMatch
      return !!doc[field!]
    }

    // If no pattern matched, default to true (don't hide)
    console.warn(`[useFormState] Unsupported depends_on expression: ${expression}`)
    return true
  } catch (e) {
    console.warn(`[useFormState] Error evaluating depends_on: ${expression}`, e)
    return true
  }
}

export function matchesCondition(
  condition: Record<string, any[]> | null | undefined,
  formData: Record<string, any>,
  entityMeta: EntityMeta | null
): boolean {
  if (!condition) return true
  for (const [field, allowedValues] of Object.entries(condition)) {
    const currentValue = formData[field]

    // Handle NULL workflow_state by treating it as the initial state
    if (currentValue == null && field === 'workflow_state') {
      const wf = entityMeta?.workflow
      const initialState = wf?.default_state || 'draft'
      const normalized = String(initialState).toLowerCase().replace(/\s+/g, '_')
      const normalizedAllowed = allowedValues.map(v => String(v).toLowerCase().replace(/\s+/g, '_'))
      if (!normalizedAllowed.includes(normalized)) return false
      continue
    }

    // Boolean field handling: treat null/undefined as false
    // Condition values can be actual booleans (false, true) or strings ("false", "true")
    const hasBooleanCondition = allowedValues.some(v => typeof v === 'boolean')
    if (hasBooleanCondition || typeof currentValue === 'boolean' || currentValue == null) {
      // Normalise current value to boolean: null/undefined/0/"false"/false → false
      let boolCurrent: boolean
      if (currentValue == null) {
        boolCurrent = false
      } else if (typeof currentValue === 'boolean') {
        boolCurrent = currentValue
      } else if (typeof currentValue === 'number') {
        boolCurrent = currentValue !== 0
      } else {
        boolCurrent = String(currentValue).toLowerCase() !== 'false' && currentValue !== '0' && !!currentValue
      }

      // Normalise each allowed value to boolean
      const boolAllowed = allowedValues.map(v => {
        if (typeof v === 'boolean') return v
        if (typeof v === 'number') return v !== 0
        return String(v).toLowerCase() !== 'false' && v !== '0' && !!v
      })

      if (!boolAllowed.includes(boolCurrent)) return false
      continue
    }

    if (currentValue == null) return false
    // Normalize: compare lowercase slugified values
    const normalized = String(currentValue).toLowerCase().replace(/\s+/g, '_')
    const normalizedAllowed = allowedValues.map(v => String(v).toLowerCase().replace(/\s+/g, '_'))
    if (!normalizedAllowed.includes(normalized)) return false
  }
  return true
}

export interface FieldState {
  visible: boolean
  editable: boolean
  required: boolean
}

export interface TabState {
  visible: boolean
  canAddChildren: boolean
}

export const useFormState = (
  entityMeta: Ref<EntityMeta | null>,
  formData: Ref<Record<string, any>>,
  linkedCounts: Ref<Record<string, number>>,
  isNew: Ref<boolean>,
) => {
  const formStateRules = computed<FormStateRules | null>(() => {
    return entityMeta.value?.form_state || null
  })

  /**
   * Check if the form is editable based on form_state.editable_when rules.
   * If no rules defined, form is always editable (default behavior).
   */
  const isFormEditable = computed<boolean>(() => {
    const rules = formStateRules.value
    const editableWhen = rules?.editable_when
    
    if (!editableWhen) return true
    
    // Handle both formats:
    // 1. Array format: ["draft", "submitted", "review"] - treat as workflow states
    // 2. Object format: {"workflow_state": ["draft", "submitted", "review"]}
    if (Array.isArray(editableWhen)) {
      // Simple array format - treat as workflow states
      const condition = { workflow_state: editableWhen }
      return matchesCondition(condition, formData.value, entityMeta.value)
    } else {
      // Object format - use as-is
      return matchesCondition(editableWhen, formData.value, entityMeta.value)
    }
  })

  /**
   * Check if children can be added based on form_state.can_add_children_when rules.
   */
  const canAddChildren = computed<boolean>(() => {
    const rules = formStateRules.value
    const canAddChildrenWhen = rules?.can_add_children_when
    
    if (!canAddChildrenWhen) return true
    
    // Handle both formats like isFormEditable
    if (Array.isArray(canAddChildrenWhen)) {
      // Simple array format - treat as workflow states
      const condition = { workflow_state: canAddChildrenWhen }
      return matchesCondition(condition, formData.value, entityMeta.value)
    } else {
      // Object format - use as-is
      return matchesCondition(canAddChildrenWhen, formData.value, entityMeta.value)
    }
  })

  /**
   * Resolve field state (visibility, editability, required) based on conditions.
   */
  const resolveFieldState = (field: FieldMeta): FieldState => {
    // Default state
    const state: FieldState = {
      visible: !field.hidden,
      editable: !field.readonly,
      required: field.required || false,
    }

    // Apply show_when: field is only visible when condition matches
    if (field.show_when) {
      state.visible = matchesCondition(field.show_when, formData.value, entityMeta.value)
    }

    // Apply display_depends_on: field visibility based on form data expression
    if (field.display_depends_on && state.visible) {
      state.visible = evaluateDependsOn(field.display_depends_on, formData.value)
    }

    // Apply editable_when: field is only editable when condition matches
    if (field.editable_when) {
      state.editable = state.editable && matchesCondition(field.editable_when, formData.value, entityMeta.value)
    }

    // Apply required_when: field is required when condition matches
    if (field.required_when) {
      state.required = matchesCondition(field.required_when, formData.value, entityMeta.value)
    }

    // Apply mandatory_depends_on: field is required based on form data expression
    if (field.mandatory_depends_on) {
      state.required = evaluateDependsOn(field.mandatory_depends_on, formData.value)
    }

    // Apply readonly_depends_on: field becomes readonly when expression is true
    if (field.readonly_depends_on && state.editable) {
      state.editable = !evaluateDependsOn(field.readonly_depends_on, formData.value)
    }

    // Apply computed_from: computed fields are always readonly
    if (field.computed_from) {
      state.editable = false
    }

    return state
  }

  /**
   * Resolve tab visibility based on tab_rules.
   */
  const resolveTabState = (linkEntity: string): TabState => {
    const defaultState: TabState = {
      visible: true,
      canAddChildren: canAddChildren.value,
    }

    // Prefer per-relation rules (metadata.links) when present
    const linkRule = entityMeta.value?.links?.find((l: any) => l?.entity === linkEntity)
    if (linkRule) {
      let visible = true

      const normalizeCondition = (c: any) => {
        if (!c) return null
        if (Array.isArray(c)) return { workflow_state: c }
        return c
      }

      const showWhen = normalizeCondition(linkRule.show_when)
      const hideWhen = normalizeCondition(linkRule.hide_when)

      if (showWhen) {
        visible = matchesCondition(showWhen, formData.value, entityMeta.value)
      }

      if (hideWhen) {
        if (matchesCondition(hideWhen, formData.value, entityMeta.value)) {
          visible = false
        }
      }

      // Apply display_depends_on (unified depends_on pattern)
      if ((linkRule as any).display_depends_on && visible) {
        visible = evaluateDependsOn((linkRule as any).display_depends_on, formData.value)
      }

      if (linkRule.require_data === 'has_lines' && visible) {
        const count = linkedCounts.value[linkEntity] || 0
        if (count === 0) {
          visible = false
        }
      }

      return {
        visible,
        canAddChildren: canAddChildren.value,
      }
    }

    const rules = formStateRules.value
    if (!rules?.tab_rules?.length) return defaultState

    const tabRule = rules.tab_rules.find(tr => tr.entity === linkEntity)
    if (!tabRule) return defaultState

    let visible = true

    // Apply show_when: tab is only visible when condition matches
    if (tabRule.show_when) {
      visible = matchesCondition(tabRule.show_when, formData.value, entityMeta.value)
    }

    // Apply hide_when: tab is hidden when condition matches
    if (tabRule.hide_when) {
      if (matchesCondition(tabRule.hide_when, formData.value, entityMeta.value)) {
        visible = false
      }
    }

    // Apply display_depends_on (unified depends_on pattern)
    if (tabRule.display_depends_on && visible) {
      visible = evaluateDependsOn(tabRule.display_depends_on, formData.value)
    }

    // Apply require_data: tab requires linked data to exist
    if (tabRule.require_data === 'has_lines' && visible) {
      const count = linkedCounts.value[linkEntity] || 0
      if (count === 0) {
        visible = false
      }
    }

    return {
      visible,
      canAddChildren: canAddChildren.value,
    }
  }

  /**
   * Get all field states as a reactive map.
   */
  const fieldStates = computed<Record<string, FieldState>>(() => {
    const fields = entityMeta.value?.fields || []
    const states: Record<string, FieldState> = {}
    for (const field of fields) {
      states[field.name] = resolveFieldState(field)
    }
    return states
  })

  /**
   * Get visible fields (filtered by show_when and hidden).
   */
  const visibleFields = computed(() => {
    const fields = entityMeta.value?.fields || []
    return fields.filter(f => {
      if (f.name === 'id' || f.name === 'created_at' || f.name === 'updated_at') return false
      const state = resolveFieldState(f)
      if (!state.visible) return false
      if (isNew.value) return !f.readonly
      return true
    })
  })

  return {
    formStateRules,
    isFormEditable,
    canAddChildren,
    resolveFieldState,
    resolveTabState,
    fieldStates,
    visibleFields,
  }
}
