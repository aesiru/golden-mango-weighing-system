import { createCrudController } from './crud.controller';

export const crateClassController = createCrudController('crateClass', {
  searchFields: ['name', 'min_weight', 'max_weight'],
});
