import prisma from '../lib/prisma';
import { HttpError } from '../lib/errors';

const VALID_TRANSITIONS: Record<string, string[]> = {
  pending: ['in-progress'],
  'in-progress': ['completed'],
  completed: ['shipped'],
  shipped: [],
};

export const orderModel = {
  async updateStatus(id: string, nextStatus: string) {
    const order = await prisma.order.findUnique({ where: { id } });
    if (!order) throw new HttpError(404, 'Order not found');

    const allowed = VALID_TRANSITIONS[order.status];
    if (!allowed || !allowed.includes(nextStatus)) {
      throw new HttpError(
        400,
        `Cannot transition from "${order.status}" to "${nextStatus}"`
      );
    }

    return prisma.order.update({
      where: { id },
      data: { status: nextStatus },
      include: { company: true, crate_class: true },
    });
  },
};
