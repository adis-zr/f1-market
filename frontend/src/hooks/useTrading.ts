import { useMutation, useQueryClient } from '@tanstack/react-query';
import { marketsApi } from '@/api/endpoints';
import { queryKeys } from './useData';
import type {
  BuySharesRequest,
  BuySharesResponse,
  SellSharesRequest,
  SellSharesResponse,
} from '@/api/types';

interface MutationContext {
  previousMarket: unknown;
  previousPosition: unknown;
  previousWallet: unknown;
}

export function useBuyShares(marketId: number) {
  const queryClient = useQueryClient();

  return useMutation<BuySharesResponse, Error, BuySharesRequest, MutationContext>({
    mutationFn: (data) => marketsApi.buyShares(marketId, data),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: queryKeys.market(marketId) });
      await queryClient.cancelQueries({ queryKey: queryKeys.position(marketId) });
      await queryClient.cancelQueries({ queryKey: queryKeys.wallet() });

      const previousMarket = queryClient.getQueryData(queryKeys.market(marketId));
      const previousPosition = queryClient.getQueryData(queryKeys.position(marketId));
      const previousWallet = queryClient.getQueryData(queryKeys.wallet());

      return { previousMarket, previousPosition, previousWallet };
    },
    onError: (_err, _newData, context) => {
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
      queryClient.invalidateQueries({ queryKey: queryKeys.market(marketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.position(marketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.priceHistory(marketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.wallet() });
      queryClient.invalidateQueries({ queryKey: queryKeys.positions });
    },
  });
}

export function useSellShares(marketId: number) {
  const queryClient = useQueryClient();

  return useMutation<SellSharesResponse, Error, SellSharesRequest, MutationContext>({
    mutationFn: (data) => marketsApi.sellShares(marketId, data),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: queryKeys.market(marketId) });
      await queryClient.cancelQueries({ queryKey: queryKeys.position(marketId) });
      await queryClient.cancelQueries({ queryKey: queryKeys.wallet() });

      const previousMarket = queryClient.getQueryData(queryKeys.market(marketId));
      const previousPosition = queryClient.getQueryData(queryKeys.position(marketId));
      const previousWallet = queryClient.getQueryData(queryKeys.wallet());

      return { previousMarket, previousPosition, previousWallet };
    },
    onError: (_err, _newData, context) => {
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
      queryClient.invalidateQueries({ queryKey: queryKeys.market(marketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.position(marketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.priceHistory(marketId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.wallet() });
      queryClient.invalidateQueries({ queryKey: queryKeys.positions });
    },
  });
}

