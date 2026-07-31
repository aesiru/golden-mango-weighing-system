import { Router } from 'express';
import { crateController } from '../controllers/crate.controller';
import { requireAuth } from '../middlewares/auth';

const router = Router();
router.use(requireAuth);

router.get('/crates', crateController.list);
router.get('/crates/:id', crateController.get);
router.post('/crates', crateController.create);
router.patch('/crates/:id', crateController.update);
router.delete('/crates/:id', crateController.remove);

export default router;
