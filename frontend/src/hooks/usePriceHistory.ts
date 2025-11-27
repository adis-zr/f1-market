import { useQuery } from '@tanstack/react-query';
import { marketsApi } from '@/api/endpoints';
import { queryKeys } from './queryKeys';
import type { PriceHistory } from '@/api/types';

export function usePriceHistory(marketId: number, limit = 100) {
  return useQuery<PriceHistory>({
    queryKey: queryKeys.priceHistory(marketId),
    queryFn: () => marketsApi.getPriceHistory(marketId, limit),
    enabled: !!marketId,
    staleTime: 1 * 60 * 1000, // 1 minute
  });
}

