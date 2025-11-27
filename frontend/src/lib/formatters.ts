/**
 * Format price to 2 decimal places with currency symbol
 */
export function formatPrice(price: number | null | undefined): string {
  if (price === null || price === undefined) return '—';
  return `$${price.toFixed(2)}`;
}

/**
 * Format price change as percentage with color indicator
 */
export function formatPriceChange(current: number, previous: number): {
  value: string;
  isPositive: boolean;
} {
  if (previous === 0) return { value: '0.00%', isPositive: false };
  const change = ((current - previous) / previous) * 100;
  return {
    value: `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`,
    isPositive: change >= 0,
  };
}

/**
 * Format PnL (Profit and Loss) with color indicator
 */
export function formatPnL(pnl: number | null | undefined): {
  value: string;
  isPositive: boolean;
} {
  if (pnl === null || pnl === undefined) return { value: '—', isPositive: false };
  return {
    value: `${pnl >= 0 ? '+' : ''}${formatPrice(pnl).replace('$', '')}`,
    isPositive: pnl >= 0,
  };
}

/**
 * Format date/time
 */
export function formatDateTime(dateString: string | null | undefined): string {
  if (!dateString) return '—';
  const date = new Date(dateString);
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format date only
 */
export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return '—';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(dateString: string | null | undefined): string {
  if (!dateString) return '—';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
  if (diffDays < 7) return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
  return formatDate(dateString);
}

/**
 * Format number with commas
 */
export function formatNumber(num: number | null | undefined): string {
  if (num === null || num === undefined) return '—';
  return num.toLocaleString('en-US', { maximumFractionDigits: 8 });
}

/**
 * Format shares quantity
 */
export function formatShares(shares: number | null | undefined): string {
  if (shares === null || shares === undefined) return '—';
  return formatNumber(shares);
}

