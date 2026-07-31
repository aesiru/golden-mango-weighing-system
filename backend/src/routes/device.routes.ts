import { Router } from 'express';
import { deviceController } from '../controllers/device.controller';
import { requireAuth } from '../middlewares/auth';
import { validate } from '../middlewares/validate';
import { deviceSchema, deviceUpdateSchema } from '../schemas/device.schema';

const router = Router();
router.use(requireAuth);

router.get('/devices', deviceController.list);
router.get('/devices/:id', deviceController.get);
router.post('/devices', validate(deviceSchema), deviceController.create);
router.patch('/devices/:id', validate(deviceUpdateSchema), deviceController.update);
router.delete('/devices/:id', deviceController.remove);

export default router;
