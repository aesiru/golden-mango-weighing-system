import { Router } from 'express';
import authRoutes from './auth.routes';
import companyRoutes from './company.routes';
import crateClassRoutes from './crateClass.routes';
import deviceRoutes from './device.routes';
import orderRoutes from './order.routes';
import crateRoutes from './crate.routes';
import readingRoutes from './reading.routes';
import userRoutes from './user.routes';
import roleRoutes from './role.routes';

export const routes = Router();

routes.use(authRoutes);
routes.use(companyRoutes);
routes.use(crateClassRoutes);
routes.use(deviceRoutes);
routes.use(orderRoutes);
routes.use(crateRoutes);
routes.use(readingRoutes);
routes.use(userRoutes);
routes.use(roleRoutes);
