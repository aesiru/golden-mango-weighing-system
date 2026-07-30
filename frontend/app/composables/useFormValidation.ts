/**
 * useFormValidation - Metadata-driven Form Validation
 * ====================================================
 * Generates validation rules from entity metadata FieldMeta definitions.
 * Uses a lightweight approach (no Zod dependency) that mirrors metadata constraints.
 */
import type { FieldMeta } from './useApiTypes'

export interface ValidationError {
  field: string
  message: string
}

export interface ValidationResult {
  valid: boolean
  errors: ValidationError[]
}

type FieldValidator = (value: unknown, formData: Record<string, unknown>) => string | null

function buildFieldValidator(field: FieldMeta): FieldValidator {
  return (value: unknown, _formData: Record<string, unknown>) => {
    // Required check
    if (field.required) {
      if (value === null || value === undefined || value === '') {
        return `${field.label} is required`
      }
    }

    // Skip further checks if empty and not required
    if (value === null || value === undefined || value === '') return null

    const strVal = String(value)

    switch (field.field_type) {
      case 'email':
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(strVal)) {
          return `${field.label} must be a valid email address`
        }
        break

      case 'phone':
        if (!/^[+\d\s()-]{7,20}$/.test(strVal)) {
          return `${field.label} must be a valid phone number`
        }
        break

      case 'int':
      case 'integer':
        if (!/^-?\d+$/.test(strVal)) {
          return `${field.label} must be a whole number`
        }
        break

      case 'float':
      case 'currency':
      case 'percent':
        if (isNaN(Number(value))) {
          return `${field.label} must be a number`
        }
        break

      case 'date':
      case 'datetime':
        if (isNaN(Date.parse(strVal))) {
          return `${field.label} must be a valid date`
        }
        break

      case 'select':
        if (field.options && field.options.length > 0) {
          const validValues = field.options.map(o => String(o.value))
          if (!validValues.includes(strVal)) {
            return `${field.label} must be one of the allowed values`
          }
        }
        break
    }

    return null
  }
}

export const useFormValidation = () => {
  /**
   * Build a validator map from entity field metadata.
   */
  function buildValidators(fields: FieldMeta[]): Map<string, FieldValidator> {
    const map = new Map<string, FieldValidator>()
    for (const field of fields) {
      if (field.hidden) continue
      map.set(field.name, buildFieldValidator(field))
    }
    return map
  }

  /**
   * Validate form data against field metadata.
   */
  function validate(
    fields: FieldMeta[],
    formData: Record<string, unknown>
  ): ValidationResult {
    const validators = buildValidators(fields)
    const errors: ValidationError[] = []

    for (const [fieldName, validator] of validators) {
      const msg = validator(formData[fieldName], formData)
      if (msg) {
        errors.push({ field: fieldName, message: msg })
      }
    }

    return { valid: errors.length === 0, errors }
  }

  /**
   * Validate a single field value.
   */
  function validateField(
    field: FieldMeta,
    value: unknown,
    formData: Record<string, unknown>
  ): string | null {
    const validator = buildFieldValidator(field)
    return validator(value, formData)
  }

  return { validate, validateField, buildValidators }
}
