import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { env } from '../config/env';
import prisma from '../lib/prisma';

export interface JwtPayload {
  sub: string;
  username: string;
  is_superuser: boolean;
}

declare global {
  namespace Express {
    interface Request {
      user?: {
        id: string;
        username: string;
        email: string;
        is_superuser: boolean;
        roles: { id: string; name: string }[];
      };
    }
  }
}

export async function requireAuth(
  req: Request,
  res: Response,
  next: NextFunction
) {
  const header = req.headers.authorization;
  if (!header?.startsWith('Bearer ')) {
    res.status(401).json({ message: 'Authentication required' });
    return;
  }

  try {
    const token = header.slice(7);
    const payload = jwt.verify(token, env.JWT_SECRET) as JwtPayload;

    const user = await prisma.user.findUnique({
      where: { id: payload.sub },
      include: { roles: { select: { id: true, name: true } } },
    });

    if (!user || !user.is_active) {
      res.status(401).json({ message: 'User not found or inactive' });
      return;
    }

    req.user = {
      id: user.id,
      username: user.username,
      email: user.email,
      is_superuser: user.is_superuser,
      roles: user.roles,
    };
    next();
  } catch {
    res.status(401).json({ message: 'Invalid or expired token' });
  }
}

export function requireSuperuser(
  req: Request,
  res: Response,
  next: NextFunction
) {
  if (!req.user?.is_superuser) {
    res.status(403).json({ message: 'Superuser access required' });
    return;
  }
  next();
}
