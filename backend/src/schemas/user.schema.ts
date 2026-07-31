import { z } from 'zod';

export const userSchema = z.object({
  body: z.object({
    username: z.string().min(3).max(50),
    email: z.string().email(),
    full_name: z.string().min(1).max(100),
    password: z.string().min(8),
    is_active: z.boolean().optional(),
    is_superuser: z.boolean().optional(),
    first_name: z.string().optional(),
    last_name: z.string().optional(),
    contact_number: z.string().optional(),
    department: z.string().optional(),
    site: z.string().optional(),
    employee_id: z.string().optional(),
    role_ids: z.array(z.string()).optional(),
  }),
});

export const userUpdateSchema = z.object({
  body: z.object({
    username: z.string().min(3).max(50).optional(),
    email: z.string().email().optional(),
    full_name: z.string().min(1).max(100).optional(),
    password: z.string().min(8).optional(),
    is_active: z.boolean().optional(),
    is_superuser: z.boolean().optional(),
    first_name: z.string().optional(),
    last_name: z.string().optional(),
    contact_number: z.string().optional(),
    department: z.string().optional(),
    site: z.string().optional(),
    employee_id: z.string().optional(),
    role_ids: z.array(z.string()).optional(),
  }),
});
