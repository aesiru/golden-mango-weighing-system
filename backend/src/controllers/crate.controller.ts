import { createCrudController } from './crud.controller';
import prisma from '../lib/prisma';
import { HttpError } from '../lib/errors';

export const crateController = createCrudController('crate', {
  idPrefix: 'CRT',
  searchFields: ['code', 'order_id', 'crate_class_id', 'target', 'counted'],
  include: { order: true, crate_class: true },
  filters: (query) => {
    const where: Record<string, any> = {};
    if (query.order_id) where.order_id = query.order_id;
    return where;
  },
  onCreateTransform: (data) => ({
    code: data.code,
    order_id: data.order_id,
    crate_class_id: data.crate_class_id,
    target: data.target ?? 50,
    counted: data.counted ?? 0,
  }),
  onBeforeDelete: async (id) => {
    const count = await prisma.reading.count({ where: { crate_id: id } });
    if (count > 0) {
      throw new HttpError(400, 'Cannot delete crate with existing readings');
    }
  },
});
