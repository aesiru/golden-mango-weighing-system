import { z } from 'zod';

// Readings are read-only via HTTP — no create/update schemas needed
// Keeping for reference
export const readingQuerySchema = z.object({
  query: z.object({
    crate_id: z.string().optional(),
    order_id: z.string().optional(),
    from: z.string().optional(),
    to: z.string().optional(),
    page: z.string().optional(),
    pageSize: z.string().optional(),
  }),
});
