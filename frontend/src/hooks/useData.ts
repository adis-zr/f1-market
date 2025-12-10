import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { sportsApi, eventsApi, marketsApi, portfolioApi } from '@/api/endpoints';
import type {
  Sport,
  League,
  Season,
  Event,
  Market,
  Position,
  Wallet,
  EventResult,
  PriceHistory,
} from '@/api/types';

// Query key factory for cache management
export const queryKeys = {
  sports: ['sports'] as const,
  leagues: (sportId?: number) => ['leagues', sportId] as const,
  seasons: (leagueId?: number) => ['seasons', leagueId] as const,
  events: (filters?: EventFilters) => ['events', filters] as const,
  event: (id: number) => ['events', id] as const,
  eventMarkets: (eventId: number) => ['events', eventId, 'markets'] as const,
  eventResults: (eventId: number) => ['events', eventId, 'results'] as const,
  markets: (filters?: MarketFilters) => ['markets', filters] as const,
  market: (id: number) => ['markets', id] as const,
  priceHistory: (marketId: number) => ['markets', marketId, 'priceHistory'] as const,
  position: (marketId: number) => ['markets', marketId, 'position'] as const,
  positions: ['positions'] as const,
  wallet: (marketId?: number) => ['wallet', marketId] as const,
  ledger: (params?: LedgerParams) => ['ledger', params] as const,
};

// Filter types
interface EventFilters {
  sport_id?: number;
  season_id?: number;
  status?: string;
}

interface MarketFilters {
  event_id?: number;
  sport_id?: number;
  status?: string;
}

interface LedgerParams {
  limit?: number;
  type?: string;
}

// Sports, Leagues, Seasons
export function useSports() {
  return useQuery<Sport[]>({
    queryKey: queryKeys.sports,
    queryFn: () => sportsApi.getSports(),
    staleTime: 10 * 60 * 1000,
  });
}

export function useLeagues(sportId?: number) {
  return useQuery<League[]>({
    queryKey: queryKeys.leagues(sportId),
    queryFn: () => sportsApi.getLeagues(sportId),
    enabled: !!sportId,
    staleTime: 10 * 60 * 1000,
  });
}

export function useSeasons(leagueId?: number) {
  return useQuery<Season[]>({
    queryKey: queryKeys.seasons(leagueId),
    queryFn: () => sportsApi.getSeasons(leagueId),
    enabled: !!leagueId,
    staleTime: 10 * 60 * 1000,
  });
}

// Events
export function useEvents(filters?: EventFilters) {
  return useQuery<Event[]>({
    queryKey: queryKeys.events(filters),
    queryFn: () => eventsApi.getEvents(filters),
    staleTime: 2 * 60 * 1000,
  });
}

export function useEvent(eventId: number) {
  return useQuery<Event>({
    queryKey: queryKeys.event(eventId),
    queryFn: () => eventsApi.getEvent(eventId),
    enabled: !!eventId,
    staleTime: 2 * 60 * 1000,
  });
}

export function useEventMarkets(eventId: number) {
  return useQuery({
    queryKey: queryKeys.eventMarkets(eventId),
    queryFn: () => eventsApi.getEventMarkets(eventId),
    enabled: !!eventId,
    staleTime: 30 * 1000,
  });
}

export function useEventResults(eventId: number) {
  return useQuery<EventResult[]>({
    queryKey: queryKeys.eventResults(eventId),
    queryFn: () => eventsApi.getEventResults(eventId),
    enabled: !!eventId,
    staleTime: 5 * 60 * 1000,
  });
}

// Markets
export function useMarkets(filters?: MarketFilters) {
  return useQuery<Market[]>({
    queryKey: queryKeys.markets(filters),
    queryFn: () => marketsApi.getMarkets(filters),
    staleTime: 30 * 1000,
  });
}

export function useMarket(marketId: number) {
  return useQuery<Market>({
    queryKey: queryKeys.market(marketId),
    queryFn: () => marketsApi.getMarket(marketId),
    enabled: !!marketId,
    staleTime: 30 * 1000,
    refetchInterval: 10 * 1000,
  });
}

export function usePriceHistory(marketId: number, limit = 100) {
  return useQuery<PriceHistory>({
    queryKey: queryKeys.priceHistory(marketId),
    queryFn: () => marketsApi.getPriceHistory(marketId, limit),
    enabled: !!marketId,
    staleTime: 1 * 60 * 1000,
  });
}

// Positions
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

// Wallet & Ledger
export function useWallet(marketId?: number) {
  return useQuery<Wallet>({
    queryKey: queryKeys.wallet(marketId),
    queryFn: () => {
      if (marketId) {
        return marketsApi.getWallet(marketId);
      }
      return portfolioApi.getWallet();
    },
    staleTime: 10 * 1000,
    refetchInterval: 5 * 1000,
  });
}

export function useLedger(params?: LedgerParams) {
  return useQuery({
    queryKey: queryKeys.ledger(params),
    queryFn: () => portfolioApi.getLedger(params),
    staleTime: 30 * 1000,
  });
}

// Portfolio (composite hook)
export function usePortfolio() {
  const { data: positions = [], ...positionsQuery } = usePositions();
  const { data: wallet } = useWallet();

  const portfolioValue = useMemo(() => {
    if (!positions || !wallet) return null;
    const positionsValue = positions.reduce((sum, pos) => {
      if (pos.current_price && pos.shares) {
        return sum + pos.current_price * pos.shares;
      }
      return sum;
    }, 0);
    return wallet.available_balance + positionsValue;
  }, [positions, wallet]);

  const totalPnL = useMemo(() => {
    if (!positions) return null;
    return positions.reduce((sum, pos) => sum + (pos.total_pnl || 0), 0);
  }, [positions]);

  return {
    positions,
    wallet,
    portfolioValue,
    totalPnL,
    ...positionsQuery,
  };
}

