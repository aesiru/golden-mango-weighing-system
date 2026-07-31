import { Router } from 'express';
import { userController } from '../controllers/user.controller';
import { requireAuth, requireSuperuser } from '../middlewares/auth';

const router = Router();
router.use(requireAuth, requireSuperuser);

router.get('/users', userController.list);
router.get('/users/:id', userController.get);
router.post('/users', userController.create);
router.patch('/users/:id', userController.update);
router.delete('/users/:id', userController.remove);

export default router;
