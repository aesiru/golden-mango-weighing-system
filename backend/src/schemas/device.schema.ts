import { z } from 'zod';

export const deviceSchema = z.object({
  body: z.object({
    name: z.string().min(1).max(100),
  }),
});

export const deviceUpdateSchema = z.object({
  body: z.object({
    name: z.string().min(1).max(100).optional(),
  }),
});
