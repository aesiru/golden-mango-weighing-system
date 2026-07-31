import { createCrudController } from './crud.controller';

export const readingController = createCrudController('reading', {
  searchFields: ['crate_id', 'order_id', 'weight_grams', 'valid'],
  include: { crate: true, order: true, device: true },
  filters: (query) => {
    const where: Record<string, any> = {};
    if (query.crate_id) where.crate_id = query.crate_id;
    if (query.order_id) where.order_id = query.order_id;
    if (query.from || query.to) {
      where.recorded_at = {};
      if (query.from) where.recorded_at.gte = new Date(query.from);
      if (query.to) where.recorded_at.lte = new Date(query.to);
    }
    return where;
  },
  allowCreate: false,
  allowUpdate: false,
  allowDelete: false,
});
