import { Router } from 'express';
import { companyController } from '../controllers/company.controller';
import { requireAuth } from '../middlewares/auth';

const router = Router();
router.use(requireAuth);

router.get('/companies', companyController.list);
router.get('/companies/:id', companyController.get);
router.post('/companies', companyController.create);
router.patch('/companies/:id', companyController.update);
router.delete('/companies/:id', companyController.remove);

export default router;
