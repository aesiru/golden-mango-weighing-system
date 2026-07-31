import { createCrudController } from './crud.controller';
import { userModel } from '../models/user.model';
import bcrypt from 'bcryptjs';
import prisma from '../lib/prisma';

export const userController = createCrudController('user', {
  idPrefix: 'USR',
  searchFields: [
    'username',
    'email',
    'full_name',
    'first_name',
    'last_name',
    'contact_number',
    'department',
    'site',
    'employee_id',
  ],
  include: { roles: { select: { id: true, name: true } } },
  sanitize: (user) => userModel.sanitize(user),
  onCreateTransform: async (data) => {
    const { password, role_ids, ...rest } = data;
    const hashed = await bcrypt.hash(password, 10);
    const result: Record<string, any> = { ...rest, hashed_password: hashed };
    if (role_ids?.length) {
      result.roles = { connect: role_ids.map((id: string) => ({ id })) };
    }
    return result;
  },
  onUpdateTransform: async (data) => {
    const { password, role_ids, ...rest } = data;
    const result: Record<string, any> = { ...rest };
    if (password) {
      result.hashed_password = await bcrypt.hash(password, 10);
    }
    if (role_ids !== undefined) {
      result.roles = { set: [], connect: role_ids.map((id: string) => ({ id })) };
    }
    return result;
  },
});
