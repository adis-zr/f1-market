import { useQuery } from '@tanstack/react-query';
import { marketsApi, portfolioApi } from '@/api/endpoints';
import { queryKeys } from './queryKeys';
import type { Position } from '@/api/types';

export function usePosition(marketId: number) {
  return useQuery<Position>({
    queryKey: queryKeys.position(marketId),
    queryFn: () => marketsApi.getPosition(marketId),
    enabled: !!marketId,
    staleTime: 30 * 1000,
  });
}

export function usePositions() {
  return useQuery<Position[]>({
    queryKey: queryKeys.positions,
    queryFn: () => portfolioApi.getPortfolio(),
    staleTime: 30 * 1000,
  });
}

