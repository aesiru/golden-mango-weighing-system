import { z } from 'zod';

export const crateClassSchema = z.object({
  body: z.object({
    name: z.string().min(1),
    min_weight: z.number().positive(),
    max_weight: z.number().positive(),
  }),
});

export const crateClassUpdateSchema = z.object({
  body: z.object({
    name: z.string().min(1).optional(),
    min_weight: z.number().positive().optional(),
    max_weight: z.number().positive().optional(),
  }),
});
