import { useQuery } from '@tanstack/react-query';
import { marketsApi } from '@/api/endpoints';
import { queryKeys } from './queryKeys';
import type { Market } from '@/api/types';

interface MarketFilters {
  event_id?: number;
  sport_id?: number;
  status?: string;
}

export function useMarkets(filters?: MarketFilters) {
  return useQuery<Market[]>({
    queryKey: queryKeys.markets(filters),
    queryFn: () => marketsApi.getMarkets(filters),
    staleTime: 30 * 1000, // 30 seconds (markets change frequently)
  });
}

export function useMarket(marketId: number) {
  return useQuery<Market>({
    queryKey: queryKeys.market(marketId),
    queryFn: () => marketsApi.getMarket(marketId),
    enabled: !!marketId,
    staleTime: 30 * 1000,
    refetchInterval: 10 * 1000, // Refetch every 10 seconds for live prices
  });
}

