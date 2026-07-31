import { z } from 'zod';

export const crateSchema = z.object({
  body: z.object({
    code: z.string().min(1),
    order_id: z.string().min(1),
    crate_class_id: z.string().min(1),
    target: z.number().positive().optional(),
    counted: z.number().min(0).optional(),
  }),
});

export const crateUpdateSchema = z.object({
  body: z.object({
    code: z.string().min(1).optional(),
    order_id: z.string().optional(),
    crate_class_id: z.string().optional(),
    target: z.number().positive().optional(),
    counted: z.number().min(0).optional(),
  }),
});
