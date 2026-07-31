import { Request, Response } from 'express';
import { createCrudController } from './crud.controller';
import { asyncHandler } from '../lib/errors';
import { orderModel } from '../models/order.model';

const base = createCrudController('order', {
  idPrefix: 'ORD',
  searchFields: ['company_id', 'crate_class_id', 'total_amount', 'current_amount', 'status'],
  include: { company: true, crate_class: true },
  filters: (query) => {
    const where: Record<string, any> = {};
    if (query.company_id) where.company_id = query.company_id;
    if (query.status) where.status = query.status;
    if (query.crate_class_id) where.crate_class_id = query.crate_class_id;
    return where;
  },
});

export const orderController = {
  ...base,
  updateStatus: asyncHandler(async (req: Request, res: Response) => {
    const id = req.params.id as string;
    const order = await orderModel.updateStatus(id, req.body.status);
    res.json({ data: order });
  }),
};
