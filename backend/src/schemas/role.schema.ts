import { z } from 'zod';

export const roleSchema = z.object({
  body: z.object({
    name: z.string().min(1),
    description: z.string().optional(),
    is_active: z.boolean().optional(),
  }),
});

export const roleUpdateSchema = z.object({
  body: z.object({
    name: z.string().min(1).optional(),
    description: z.string().optional(),
    is_active: z.boolean().optional(),
  }),
});
