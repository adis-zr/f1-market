import { useMutation, useQueryClient } from '@tanstack/react-query';
import { marketsApi } from '@/api/endpoints';
import { queryKeys } from './queryKeys';
import type { SellSharesRequest, SellSharesResponse } from '@/api/types';

export function useSellShares(marketId: number) {
  const queryClient = useQueryClient();

  return useMutation<SellSharesResponse, Error, SellSharesRequest>({
    mutationFn: (data) => marketsApi.sellShares(marketId, data),
    onMutate: async (newData) => {
      // Cancel outgoing queries
      await queryClient.cancelQueries({ queryKey: queryKeys.market(marketId) });
      await queryClient.cancelQueries({ queryKey: queryKeys.position(marketId) });
      await queryClient.cancelQueries({ queryKey: queryKeys.wallet() });

      // Snapshot previous values
      const previousMarket = queryClient.getQueryData(queryKeys.market(marketId));
      const previousPosition = queryClient.getQueryData(queryKeys.position(marketId));
      const previousWallet = queryClient.getQueryData(queryKeys.wallet());

      return { previousMarket, previousPosition, previousWallet };
    },
    onError: (err, newData, context) => {
      // Rollback optimistic updates
      if (context?.previousMarket) {
        queryClient.setQueryData(queryKeys.market(marketId), context.previousMarket);
      }
      if (context?.previousPosition) {
        queryClient.setQueryData(queryKeys.position(marketId), context.previousPosition);
      }
      if (context?.previousWallet) {
        queryClient.setQueryData(queryKeys.wallet(), context.previousWallet);
      }
    },
    onSuccess: () => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: queryKeys.market(marketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.position(marketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.priceHistory(marketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.wallet() });
      queryClient.invalidateQueries({ queryKey: queryKeys.portfolio });
    },
  });
}

