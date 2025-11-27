import { useQuery } from '@tanstack/react-query';
import { portfolioApi, marketsApi } from '@/api/endpoints';
import { queryKeys } from './queryKeys';
import type { Wallet } from '@/api/types';

export function useWallet(marketId?: number) {
  return useQuery<Wallet>({
    queryKey: queryKeys.wallet(marketId),
    queryFn: () => {
      if (marketId) {
        return marketsApi.getWallet(marketId);
      }
      return portfolioApi.getWallet();
    },
    staleTime: 10 * 1000, // 10 seconds
    refetchInterval: 5 * 1000, // Refetch every 5 seconds
  });
}

export function useLedger(params?: { limit?: number; type?: string }) {
  return useQuery({
    queryKey: queryKeys.ledger(params),
    queryFn: () => portfolioApi.getLedger(params),
    staleTime: 30 * 1000,
  });
}

