import { z } from 'zod';

export const companySchema = z.object({
  body: z.object({
    name: z.string().optional(),
    contact_person: z.string().optional(),
    email: z.string().email().optional(),
    phone: z.string().optional(),
    address: z.string().optional(),
    registration_date: z.string().datetime().optional(),
    status: z.enum(['pending', 'approved']).optional(),
  }),
});

export const companyUpdateSchema = z.object({
  body: z.object({
    name: z.string().optional(),
    contact_person: z.string().optional(),
    email: z.string().email().optional(),
    phone: z.string().optional(),
    address: z.string().optional(),
    registration_date: z.string().datetime().optional(),
    status: z.enum(['pending', 'approved']).optional(),
  }),
});
