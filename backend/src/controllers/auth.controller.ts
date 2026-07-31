import { Request, Response } from 'express';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { asyncHandler } from '../lib/errors';
import { env } from '../config/env';
import { shortId } from '../lib/ids';
import prisma from '../lib/prisma';
import { userModel } from '../models/user.model';

export const authController = {
  register: asyncHandler(async (req: Request, res: Response) => {
    const data = req.body;

    const existing = await prisma.user.findFirst({
      where: {
        OR: [{ username: data.username }, { email: data.email }],
      },
    });
    if (existing) {
      res.status(409).json({ message: 'Username or email already taken' });
      return;
    }

    const hashed = await bcrypt.hash(data.password, 10);
    const user = await prisma.user.create({
      data: {
        id: shortId('USR'),
        username: data.username,
        email: data.email,
        full_name: data.full_name,
        hashed_password: hashed,
        first_name: data.first_name,
        last_name: data.last_name,
        contact_number: data.contact_number,
        department: data.department,
        site: data.site,
        employee_id: data.employee_id,
      },
    });

    const token = jwt.sign(
      { sub: user.id, username: user.username, is_superuser: user.is_superuser },
      env.JWT_SECRET,
      { expiresIn: env.JWT_EXPIRES_IN as any }
    );

    res.status(201).json({ token, user: userModel.sanitize(user) });
  }),

  login: asyncHandler(async (req: Request, res: Response) => {
    const { login, password } = req.body;

    const user = await prisma.user.findFirst({
      where: {
        OR: [{ username: login }, { email: login }],
      },
      include: { roles: { select: { id: true, name: true } } },
    });

    if (!user) {
      res.status(401).json({ message: 'Invalid credentials' });
      return;
    }

    if (!user.is_active) {
      res.status(401).json({ message: 'Account is inactive' });
      return;
    }

    const valid = await bcrypt.compare(password, user.hashed_password);
    if (!valid) {
      res.status(401).json({ message: 'Invalid credentials' });
      return;
    }

    const token = jwt.sign(
      { sub: user.id, username: user.username, is_superuser: user.is_superuser },
      env.JWT_SECRET,
      { expiresIn: env.JWT_EXPIRES_IN as any }
    );

    res.json({ token, user: userModel.sanitize(user) });
  }),

  me: asyncHandler(async (req: Request, res: Response) => {
    res.json({ user: req.user });
  }),
};
