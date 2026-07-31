import { createCrudController } from './crud.controller';

export const companyController = createCrudController('company', {
  idPrefix: 'COMP',
  searchFields: ['name', 'contact_person', 'email', 'phone', 'address', 'status'],
});
