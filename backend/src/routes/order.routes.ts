import { Router } from 'express';
import { orderController } from '../controllers/order.controller';
import { requireAuth } from '../middlewares/auth';
import { validate } from '../middlewares/validate';
import { orderStatusSchema } from '../schemas/order.schema';

const router = Router();
router.use(requireAuth);

router.get('/orders', orderController.list);
router.get('/orders/:id', orderController.get);
router.post('/orders', orderController.create);
router.patch('/orders/:id', orderController.update);
router.delete('/orders/:id', orderController.remove);
router.patch('/orders/:id/status', validate(orderStatusSchema), orderController.updateStatus);

export default router;
