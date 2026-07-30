import { describe, it, expect } from 'vitest'

describe('useFormValidation', () => {
  it('should be importable', () => {
    const { validateField, validate } = useFormValidation()
    expect(typeof validateField).toBe('function')
    expect(typeof validate).toBe('function')
  })

  it('should return error for required empty field', () => {
    const { validateField } = useFormValidation()
    const field = { name: 'title', label: 'Title', field_type: 'string', required: true } as any
    const error = validateField(field, '', {})
    expect(error).not.toBeNull()
    expect(error).toContain('required')
  })

  it('should pass for required field with value', () => {
    const { validateField } = useFormValidation()
    const field = { name: 'title', label: 'Title', field_type: 'string', required: true } as any
    const error = validateField(field, 'Hello', {})
    expect(error).toBeNull()
  })

  it('should validate email format', () => {
    const { validateField } = useFormValidation()
    const field = { name: 'email', label: 'Email', field_type: 'email', required: false } as any

    expect(validateField(field, 'not-an-email', {})).not.toBeNull()
    expect(validateField(field, 'user@example.com', {})).toBeNull()
  })

  it('should validate int fields', () => {
    const { validateField } = useFormValidation()
    const field = { name: 'qty', label: 'Quantity', field_type: 'int', required: false } as any

    expect(validateField(field, 'abc', {})).not.toBeNull()
    expect(validateField(field, 42, {})).toBeNull()
  })

  it('should skip validation for empty non-required fields', () => {
    const { validateField } = useFormValidation()
    const field = { name: 'notes', label: 'Notes', field_type: 'string', required: false } as any
    expect(validateField(field, '', {})).toBeNull()
  })

  it('should validate entire form and report errors', () => {
    const { validate } = useFormValidation()
    const fields = [
      { name: 'title', label: 'Title', field_type: 'string', required: true },
      { name: 'email', label: 'Email', field_type: 'email', required: false },
    ] as any[]

    const data = { title: '', email: 'bad' }
    const result = validate(fields, data)
    expect(result.valid).toBe(false)
    expect(result.errors.length).toBeGreaterThanOrEqual(2)
    expect(result.errors.some((e: any) => e.field === 'title')).toBe(true)
    expect(result.errors.some((e: any) => e.field === 'email')).toBe(true)
  })

  it('should return valid for correct form data', () => {
    const { validate } = useFormValidation()
    const fields = [
      { name: 'title', label: 'Title', field_type: 'string', required: true },
      { name: 'email', label: 'Email', field_type: 'email', required: false },
    ] as any[]

    const data = { title: 'Test', email: 'user@test.com' }
    const result = validate(fields, data)
    expect(result.valid).toBe(true)
    expect(result.errors.length).toBe(0)
  })
})
