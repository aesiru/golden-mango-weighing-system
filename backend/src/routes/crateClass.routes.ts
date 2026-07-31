import { Router } from 'express';
import { crateClassController } from '../controllers/crateClass.controller';
import { requireAuth } from '../middlewares/auth';

const router = Router();
router.use(requireAuth);

router.get('/crate-classes', crateClassController.list);
router.get('/crate-classes/:id', crateClassController.get);
router.post('/crate-classes', crateClassController.create);
router.patch('/crate-classes/:id', crateClassController.update);
router.delete('/crate-classes/:id', crateClassController.remove);

export default router;
