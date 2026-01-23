import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState, useEffect, useRef, useMemo } from 'react';
import { replayApi } from '@/api/endpoints';
import type {
  ReplayState,
  ReplayAdvanceResponse,
  ReplayBuyResponse,
  ReplaySellResponse,
  ReplayEstimateResponse,
  ReplayLeaderboard,
  ReplayDifficulty,
} from '@/api/types';

// Query key factory for replay cache management
export const replayQueryKeys = {
  session: ['replay', 'session'] as const,
  markets: ['replay', 'markets'] as const,
  market: (id: number) => ['replay', 'markets', id] as const,
  portfolio: ['replay', 'portfolio'] as const,
  wallet: ['replay', 'wallet'] as const,
  ledger: ['replay', 'ledger'] as const,
  races: ['replay', 'races'] as const,
  raceResults: (num: number) => ['replay', 'races', num, 'results'] as const,
  priceHistory: (marketId: number) => ['replay', 'markets', marketId, 'priceHistory'] as const,
  leaderboard: ['replay', 'leaderboard'] as const,
};

// =============================================================================
// Query Hooks
// =============================================================================

export function useReplaySession() {
  return useQuery<ReplayState>({
    queryKey: replayQueryKeys.session,
    queryFn: () => replayApi.getSession(),
    staleTime: 30 * 1000,
    retry: false, // Don't retry on 404 (no session)
  });
}

export function useReplayMarkets() {
  return useQuery({
    queryKey: replayQueryKeys.markets,
    queryFn: async () => {
      const data = await replayApi.getMarkets();
      return data.markets;
    },
    staleTime: 30 * 1000,
    refetchInterval: 10 * 1000,
  });
}

export function useReplayMarket(marketId: number) {
  return useQuery({
    queryKey: replayQueryKeys.market(marketId),
    queryFn: () => replayApi.getMarket(marketId),
    enabled: !!marketId,
    staleTime: 30 * 1000,
    refetchInterval: 10 * 1000,
  });
}

export function useReplayPortfolio() {
  return useQuery({
    queryKey: replayQueryKeys.portfolio,
    queryFn: () => replayApi.getPortfolio(),
    staleTime: 30 * 1000,
  });
}

export function useReplayWallet() {
  return useQuery({
    queryKey: replayQueryKeys.wallet,
    queryFn: () => replayApi.getWallet(),
    staleTime: 10 * 1000,
    refetchInterval: 5 * 1000,
  });
}

export function useReplayLedger(limit = 100) {
  return useQuery({
    queryKey: replayQueryKeys.ledger,
    queryFn: async () => {
      const data = await replayApi.getLedger(limit);
      return data.ledger;
    },
    staleTime: 30 * 1000,
  });
}

export function useReplayRaces() {
  return useQuery({
    queryKey: replayQueryKeys.races,
    queryFn: async () => {
      const data = await replayApi.getRaces();
      return data.races;
    },
    staleTime: 60 * 1000,
  });
}

export function useReplayRaceResults(raceNumber: number) {
  return useQuery({
    queryKey: replayQueryKeys.raceResults(raceNumber),
    queryFn: () => replayApi.getRaceResults(raceNumber),
    enabled: !!raceNumber && raceNumber >= 1 && raceNumber <= 24,
    staleTime: 5 * 60 * 1000, // Historical data doesn't change
  });
}

export function useReplayPriceHistory(marketId: number, limit = 100) {
  return useQuery({
    queryKey: replayQueryKeys.priceHistory(marketId),
    queryFn: async () => {
      const data = await replayApi.getPriceHistory(marketId, limit);
      return data.history;
    },
    enabled: !!marketId,
    staleTime: 1 * 60 * 1000,
  });
}

export function useReplayLeaderboard(limit = 50, difficulty?: ReplayDifficulty) {
  return useQuery<ReplayLeaderboard>({
    queryKey: [...replayQueryKeys.leaderboard, difficulty] as const,
    queryFn: () => replayApi.getLeaderboard(limit, difficulty),
    staleTime: 2 * 60 * 1000,
  });
}

// =============================================================================
// Mutation Hooks
// =============================================================================

export function useStartReplay() {
  const queryClient = useQueryClient();

  return useMutation<ReplayState, Error, ReplayDifficulty | undefined>({
    mutationFn: (difficulty) => replayApi.startReplay(difficulty),
    onSuccess: (data) => {
      queryClient.setQueryData(replayQueryKeys.session, data);
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.markets });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.portfolio });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.wallet });
    },
  });
}

export function useAdvanceRace() {
  const queryClient = useQueryClient();

  return useMutation<ReplayAdvanceResponse, Error>({
    mutationFn: () => replayApi.advanceRace(),
    onSuccess: (data) => {
      queryClient.setQueryData(replayQueryKeys.session, data.new_state);
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.markets });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.portfolio });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.wallet });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.ledger });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.races });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.leaderboard });
    },
  });
}

export function useResetReplay() {
  const queryClient = useQueryClient();

  return useMutation<ReplayState, Error, ReplayDifficulty | undefined>({
    mutationFn: (difficulty) => replayApi.resetReplay(difficulty),
    onSuccess: (data) => {
      queryClient.setQueryData(replayQueryKeys.session, data);
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.markets });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.portfolio });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.wallet });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.ledger });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.races });
    },
  });
}

interface ReplayMutationContext {
  previousSession: ReplayState | undefined;
  previousWallet: { balance: number; locked_balance: number } | undefined;
}

export function useReplayBuyShares(marketId: number) {
  const queryClient = useQueryClient();

  return useMutation<ReplayBuyResponse, Error, number, ReplayMutationContext>({
    mutationFn: (quantity) => replayApi.buyShares(marketId, quantity),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: replayQueryKeys.session });
      await queryClient.cancelQueries({ queryKey: replayQueryKeys.wallet });

      const previousSession = queryClient.getQueryData<ReplayState>(replayQueryKeys.session);
      const previousWallet = queryClient.getQueryData<{ balance: number; locked_balance: number }>(
        replayQueryKeys.wallet
      );

      return { previousSession, previousWallet };
    },
    onError: (_err, _quantity, context) => {
      if (context?.previousSession) {
        queryClient.setQueryData(replayQueryKeys.session, context.previousSession);
      }
      if (context?.previousWallet) {
        queryClient.setQueryData(replayQueryKeys.wallet, context.previousWallet);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.session });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.markets });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.market(marketId) });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.priceHistory(marketId) });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.portfolio });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.wallet });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.ledger });
    },
  });
}

export function useReplaySellShares(marketId: number) {
  const queryClient = useQueryClient();

  return useMutation<ReplaySellResponse, Error, number, ReplayMutationContext>({
    mutationFn: (quantity) => replayApi.sellShares(marketId, quantity),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: replayQueryKeys.session });
      await queryClient.cancelQueries({ queryKey: replayQueryKeys.wallet });

      const previousSession = queryClient.getQueryData<ReplayState>(replayQueryKeys.session);
      const previousWallet = queryClient.getQueryData<{ balance: number; locked_balance: number }>(
        replayQueryKeys.wallet
      );

      return { previousSession, previousWallet };
    },
    onError: (_err, _quantity, context) => {
      if (context?.previousSession) {
        queryClient.setQueryData(replayQueryKeys.session, context.previousSession);
      }
      if (context?.previousWallet) {
        queryClient.setQueryData(replayQueryKeys.wallet, context.previousWallet);
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.session });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.markets });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.market(marketId) });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.priceHistory(marketId) });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.portfolio });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.wallet });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.ledger });
    },
  });
}

// Variant that accepts marketId in the mutation (for selling from different markets)
export function useReplaySellSharesDynamic() {
  const queryClient = useQueryClient();

  return useMutation<ReplaySellResponse, Error, { marketId: number; quantity: number }, ReplayMutationContext>({
    mutationFn: ({ marketId, quantity }) => replayApi.sellShares(marketId, quantity),
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: replayQueryKeys.session });
      await queryClient.cancelQueries({ queryKey: replayQueryKeys.wallet });

      const previousSession = queryClient.getQueryData<ReplayState>(replayQueryKeys.session);
      const previousWallet = queryClient.getQueryData<{ balance: number; locked_balance: number }>(
        replayQueryKeys.wallet
      );

      return { previousSession, previousWallet };
    },
    onError: (_err, _vars, context) => {
      if (context?.previousSession) {
        queryClient.setQueryData(replayQueryKeys.session, context.previousSession);
      }
      if (context?.previousWallet) {
        queryClient.setQueryData(replayQueryKeys.wallet, context.previousWallet);
      }
    },
    onSuccess: (_data, { marketId }) => {
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.session });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.markets });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.market(marketId) });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.priceHistory(marketId) });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.portfolio });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.wallet });
      queryClient.invalidateQueries({ queryKey: replayQueryKeys.ledger });
    },
  });
}

// =============================================================================
// Utility Hooks
// =============================================================================

// Cost estimation hook with debounce
export function useReplayEstimateCost(
  marketId: number,
  quantity: number,
  side: 'buy' | 'sell',
  debounceMs = 300
) {
  const [estimate, setEstimate] = useState<ReplayEstimateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!quantity || quantity <= 0 || !marketId) {
      setEstimate(null);
      setError(null);
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const timeoutId = setTimeout(async () => {
      abortControllerRef.current = new AbortController();
      setIsLoading(true);
      setError(null);

      try {
        const result = await replayApi.estimateCost(marketId, quantity, side);
        setEstimate(result);
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') {
          return;
        }
        setError('Failed to estimate cost');
        setEstimate(null);
      } finally {
        setIsLoading(false);
      }
    }, debounceMs);

    return () => {
      clearTimeout(timeoutId);
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [marketId, quantity, side, debounceMs]);

  return { estimate, isLoading, error };
}

// Composite hook for replay state
export function useReplay() {
  const sessionQuery = useReplaySession();
  const walletQuery = useReplayWallet();

  const session = sessionQuery.data?.session;
  const wallet = sessionQuery.data?.wallet || walletQuery.data;
  const currentRaceInfo = sessionQuery.data?.current_race_info;
  const markets = sessionQuery.data?.markets || [];
  const positions = sessionQuery.data?.positions || [];
  const totalPnL = sessionQuery.data?.total_pnl;
  const allRaces = sessionQuery.data?.all_races || [];

  const hasActiveSession = !!session && session.status === 'active';
  const isCompleted = !!session && session.status === 'completed';
  const currentRace = session?.current_race || 0;

  // Calculate portfolio value
  const portfolioValue = useMemo(() => {
    if (!wallet || !positions) return null;
    const positionsValue = positions.reduce((sum, pos) => {
      return sum + pos.current_price * pos.shares;
    }, 0);
    return wallet.balance + positionsValue;
  }, [wallet, positions]);

  return {
    // State
    session,
    wallet,
    currentRaceInfo,
    markets,
    positions,
    totalPnL,
    allRaces,
    portfolioValue,

    // Computed
    hasActiveSession,
    isCompleted,
    currentRace,

    // Query state
    isLoading: sessionQuery.isLoading,
    isError: sessionQuery.isError,
    error: sessionQuery.error,
    refetch: sessionQuery.refetch,
  };
}
