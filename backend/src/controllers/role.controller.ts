import { createCrudController } from './crud.controller';

export const roleController = createCrudController('role', {
  searchFields: ['name', 'description', 'is_active'],
  include: { users: { select: { id: true, username: true } } },
});
