import { Router } from 'express';
import { roleController } from '../controllers/role.controller';
import { requireAuth, requireSuperuser } from '../middlewares/auth';

const router = Router();
router.use(requireAuth, requireSuperuser);

router.get('/roles', roleController.list);
router.get('/roles/:id', roleController.get);
router.post('/roles', roleController.create);
router.patch('/roles/:id', roleController.update);
router.delete('/roles/:id', roleController.remove);

export default router;
