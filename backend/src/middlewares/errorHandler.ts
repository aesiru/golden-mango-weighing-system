import { Request, Response, NextFunction } from 'express';
import { HttpError } from '../lib/errors';

export function notFound(req: Request, _res: Response, next: NextFunction) {
  next(new HttpError(404, `Not found: ${req.method} ${req.path}`));
}

export function errorHandler(
  err: Error,
  _req: Request,
  res: Response,
  _next: NextFunction
) {
  if (err instanceof HttpError) {
    res.status(err.status).json({ message: err.message });
    return;
  }

  // Prisma P2002: unique constraint violation
  if (
    'code' in err &&
    (err as any).code === 'P2002'
  ) {
    const targets = (err as any).meta?.target as string[] | undefined;
    const fields = targets?.join(', ') || 'field';
    res.status(409).json({ message: `Duplicate value for ${fields}` });
    return;
  }

  // Prisma P2025: record not found
  if (
    'code' in err &&
    (err as any).code === 'P2025'
  ) {
    res.status(404).json({ message: 'Record not found' });
    return;
  }

  console.error(err);
  res.status(500).json({ message: 'Internal server error' });
}
