import { z } from 'zod';

export const orderSchema = z.object({
  body: z.object({
    company_id: z.string().optional(),
    crate_class_id: z.string().min(1),
    total_amount: z.number().optional(),
    current_amount: z.number().optional(),
    status: z.enum(['pending', 'in-progress', 'completed', 'shipped']).optional(),
  }),
});

export const orderUpdateSchema = z.object({
  body: z.object({
    company_id: z.string().optional(),
    crate_class_id: z.string().optional(),
    total_amount: z.number().optional(),
    current_amount: z.number().optional(),
    status: z.enum(['pending', 'in-progress', 'completed', 'shipped']).optional(),
  }),
});

export const orderStatusSchema = z.object({
  body: z.object({
    status: z.enum(['pending', 'in-progress', 'completed', 'shipped']),
  }),
});
