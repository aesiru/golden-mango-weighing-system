import crypto from 'crypto';

export function shortId(prefix: string): string {
  const hex = crypto.randomBytes(4).toString('hex').toUpperCase();
  return `${prefix}-${hex}`;
}
