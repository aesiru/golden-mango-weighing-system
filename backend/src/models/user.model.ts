import bcrypt from 'bcryptjs';
import prisma from '../lib/prisma';

export const userModel = {
  sanitize(user: any) {
    const { hashed_password, ...rest } = user;
    return rest;
  },
};
