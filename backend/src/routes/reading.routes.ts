import { Router } from 'express';
import { readingController } from '../controllers/reading.controller';
import { requireAuth } from '../middlewares/auth';

const router = Router();
router.use(requireAuth);

router.get('/readings', readingController.list);
router.get('/readings/:id', readingController.get);

export default router;
