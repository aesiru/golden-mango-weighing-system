import { createCrudController } from './crud.controller';

export const deviceController = createCrudController('device', {
  idPrefix: 'DEV',
  searchFields: ['name'],
});
