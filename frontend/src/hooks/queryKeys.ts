/**
 * Centralized query keys for React Query
 */
export const queryKeys = {
  // Auth
  currentUser: ['currentUser'] as const,

  // Sports & Leagues
  sports: ['sports'] as const,
  leagues: (sportId?: number) => ['leagues', sportId] as const,
  seasons: (leagueId?: number) => ['seasons', leagueId] as const,

  // Events
  events: (filters?: { sport_id?: number; season_id?: number; status?: string }) =>
    ['events', filters] as const,
  event: (id: number) => ['events', id] as const,
  eventMarkets: (eventId: number) => ['events', eventId, 'markets'] as const,
  eventResults: (eventId: number) => ['events', eventId, 'results'] as const,

  // Markets
  markets: (filters?: { event_id?: number; sport_id?: number; status?: string }) =>
    ['markets', filters] as const,
  market: (id: number) => ['markets', id] as const,
  priceHistory: (marketId: number) => ['markets', marketId, 'priceHistory'] as const,
  position: (marketId: number) => ['markets', marketId, 'position'] as const,
  wallet: (marketId?: number) => ['wallet', marketId] as const,

  // Portfolio
  portfolio: ['portfolio'] as const,
  positions: ['positions'] as const,

  // Wallet & Ledger
  ledger: (params?: { limit?: number; type?: string }) => ['ledger', params] as const,
};

