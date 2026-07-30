export interface Stat {
  title: string;
  icon: string;
  value: number;
  variation: number;
}

export type Period = 'daily' | 'weekly' | 'monthly';
export type Range = 'current' | 'previous' | 'last-7' | 'last-30' | 'last-90';
