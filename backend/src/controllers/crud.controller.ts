import { Request, Response } from 'express';
import { asyncHandler } from '../lib/errors';
import { shortId } from '../lib/ids';
import prisma from '../lib/prisma';
import { Prisma } from '@prisma/client';

type PrismaModel = keyof typeof prisma & {
  [K in keyof typeof prisma]: (typeof prisma)[K] extends { findMany: any }
    ? K
    : never;
}[keyof typeof prisma];

type ModelDelegate = {
  findMany: Function;
  findUnique: Function;
  create: Function;
  update: Function;
  delete: Function;
  count: Function;
};

interface CrudOptions {
  idPrefix?: string;
  searchFields: string[];
  include?: Record<string, any>;
  filters?: (query: Record<string, any>) => Record<string, any>;
  onBeforeDelete?: (id: string) => Promise<void>;
  onCreateTransform?: (data: Record<string, any>) => Record<string, any> | Promise<Record<string, any>>;
  onUpdateTransform?: (data: Record<string, any>) => Record<string, any> | Promise<Record<string, any>>;
  sanitize?: (record: any) => any;
  allowCreate?: boolean;
  allowUpdate?: boolean;
  allowDelete?: boolean;
}

export function createCrudController(modelName: string, options: CrudOptions) {
  const delegate = (prisma as any)[modelName] as ModelDelegate;
  const {
    idPrefix,
    include,
    filters: buildFilters,
    onBeforeDelete,
    onCreateTransform,
    onUpdateTransform,
    sanitize,
    allowCreate = true,
    allowUpdate = true,
    allowDelete = true,
  } = options;

  const list = asyncHandler(async (req: Request, res: Response) => {
    const page = Math.max(1, parseInt(req.query.page as string) || 1);
    const pageSize = Math.min(100, Math.max(1, parseInt(req.query.pageSize as string) || 20));
    const where = buildFilters ? buildFilters(req.query) : {};

    const [total, records] = await Promise.all([
      delegate.count({ where }),
      delegate.findMany({
        where,
        include,
        skip: (page - 1) * pageSize,
        take: pageSize,
        orderBy: { created_at: 'desc' },
      }),
    ]);

    res.json({
      data: sanitize ? records.map(sanitize) : records,
      total,
      page,
      pageSize,
    });
  });

  const get = asyncHandler(async (req: Request, res: Response) => {
    const id = req.params.id as string;
    const record = await delegate.findUnique({
      where: { id },
      include,
    });
    if (!record) {
      res.status(404).json({ message: `${modelName} not found` });
      return;
    }
    res.json({ data: sanitize ? sanitize(record) : record });
  });

  const create = asyncHandler(async (req: Request, res: Response) => {
    if (!allowCreate) {
      res.status(405).json({ message: 'Method not allowed' });
      return;
    }
    let data = { ...req.body };
    if (onCreateTransform) data = await onCreateTransform(data);
    if (idPrefix) data.id = shortId(idPrefix);

    const record = await delegate.create({ data, include });
    res.status(201).json({ data: sanitize ? sanitize(record) : record });
  });

  const update = asyncHandler(async (req: Request, res: Response) => {
    if (!allowUpdate) {
      res.status(405).json({ message: 'Method not allowed' });
      return;
    }
    let data = { ...req.body };
    if (onUpdateTransform) data = await onUpdateTransform(data);

    const id = req.params.id as string;
    const record = await delegate.update({
      where: { id },
      data,
      include,
    });
    res.json({ data: sanitize ? sanitize(record) : record });
  });

  const remove = asyncHandler(async (req: Request, res: Response) => {
    if (!allowDelete) {
      res.status(405).json({ message: 'Method not allowed' });
      return;
    }
    const id = req.params.id as string;
    if (onBeforeDelete) await onBeforeDelete(id);
    await delegate.delete({ where: { id } });
    res.json({ message: 'Deleted' });
  });

  return { list, get, create, update, remove };
}
