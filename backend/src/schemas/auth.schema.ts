import { z } from 'zod';

export const registerSchema = z.object({
  body: z.object({
    username: z.string().min(3).max(50),
    email: z.string().email(),
    full_name: z.string().min(1).max(100),
    password: z.string().min(8),
    first_name: z.string().optional(),
    last_name: z.string().optional(),
    contact_number: z.string().optional(),
    department: z.string().optional(),
    site: z.string().optional(),
    employee_id: z.string().optional(),
  }),
});

export const loginSchema = z.object({
  body: z.object({
    login: z.string().min(1),
    password: z.string().min(1),
  }),
});

export type RegisterInput = z.infer<typeof registerSchema>['body'];
export type LoginInput = z.infer<typeof loginSchema>['body'];
