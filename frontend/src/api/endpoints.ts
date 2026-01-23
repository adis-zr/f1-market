import apiClient from './client';
import type {
  Sport,
  League,
  Season,
  Event,
  Market,
  Position,
  Wallet,
  LedgerEntry,
  EventResult,
  PriceHistory,
  User,
  BuySharesRequest,
  SellSharesRequest,
  BuySharesResponse,
  SellSharesResponse,
  ReplayState,
  ReplayAdvanceResponse,
  ReplayBuyResponse,
  ReplaySellResponse,
  ReplayEstimateResponse,
  ReplayMarket,
  ReplayPosition,
  ReplayRace,
  ReplayRaceResult,
  ReplayLeaderboard,
  ReplayPriceHistoryEntry,
  ReplayLedgerEntry,
  ReplayPnL,
} from './types';

// Generic fetch helpers
const get = <T>(url: string, params?: object) =>
  apiClient.get<T>(url, { params }).then((r) => r.data);

const post = <T>(url: string, data?: object) =>
  apiClient.post<T>(url, data).then((r) => r.data);

// Auth
export const authApi = {
  getCurrentUser: () => get<User>('/auth/me'),
  logout: () => post<void>('/auth/logout'),
};

// Sports & Leagues
export const sportsApi = {
  getSports: () => get<Sport[]>('/api/sports'),
  getLeagues: (sportId?: number) => get<League[]>('/api/leagues', sportId ? { sport_id: sportId } : {}),
  getSeasons: (leagueId?: number) => get<Season[]>('/api/seasons', leagueId ? { league_id: leagueId } : {}),
};

// Events
export const eventsApi = {
  getEvents: (filters?: { sport_id?: number; season_id?: number; status?: string }) =>
    get<Event[]>('/api/events', filters),
  getEvent: (eventId: number) => get<Event>(`/api/events/${eventId}`),
  getEventMarkets: (eventId: number) => get<Market[]>(`/api/events/${eventId}/markets`),
  getEventResults: (eventId: number) => get<EventResult[]>(`/api/events/${eventId}/results`),
};

// Estimate response types
export interface EstimateBuyResponse {
  side: 'buy';
  quantity: number;
  estimated_cost: number;
  price_per_share: number;
  current_supply: number;
}

export interface EstimateSellResponse {
  side: 'sell';
  quantity: number;
  estimated_payout: number;
  price_per_share: number;
  current_supply: number;
}

export type EstimateResponse = EstimateBuyResponse | EstimateSellResponse;

// Markets
export const marketsApi = {
  getMarkets: (filters?: { event_id?: number; sport_id?: number; status?: string }) =>
    get<Market[]>('/api/markets', filters),
  getMarket: (marketId: number) => get<Market>(`/api/markets/${marketId}`),
  getPriceHistory: (marketId: number, limit = 100) =>
    get<PriceHistory>(`/api/markets/${marketId}/price-history`, { limit }),
  getPosition: (marketId: number) => get<Position>(`/api/markets/${marketId}/positions`),
  getWallet: (marketId: number) => get<Wallet>(`/api/markets/${marketId}/wallet`),
  buyShares: (marketId: number, data: BuySharesRequest) =>
    post<BuySharesResponse>(`/api/markets/${marketId}/buy`, data),
  sellShares: (marketId: number, data: SellSharesRequest) =>
    post<SellSharesResponse>(`/api/markets/${marketId}/sell`, data),
  estimateCost: (marketId: number, quantity: number, side: 'buy' | 'sell') =>
    post<EstimateResponse>(`/api/markets/${marketId}/estimate`, { quantity, side }),
};

// Portfolio & Wallet
export const portfolioApi = {
  getPortfolio: () => get<Position[]>('/api/portfolio'),
  getWallet: () => get<Wallet>('/api/wallet'),
  getLedger: (params?: { limit?: number; type?: string }) => get<LedgerEntry[]>('/api/wallet/ledger', params),
};

// =============================================================================
// Replay Mode API
// =============================================================================

export const replayApi = {
  // Session management
  startReplay: (difficulty?: 'easy' | 'medium' | 'hard') =>
    post<ReplayState>('/api/replay/start', difficulty ? { difficulty } : undefined),
  getSession: () => get<ReplayState>('/api/replay/session'),
  resetReplay: (difficulty?: 'easy' | 'medium' | 'hard') =>
    post<ReplayState>('/api/replay/reset', difficulty ? { difficulty } : undefined),

  // Race progression
  advanceRace: () => post<ReplayAdvanceResponse>('/api/replay/advance'),
  settleRace: () => post<ReplayAdvanceResponse>('/api/replay/settle'),

  // Markets
  getMarkets: () => get<{ markets: ReplayMarket[] }>('/api/replay/markets'),
  getMarket: (marketId: number) =>
    get<{ market: ReplayMarket; position: ReplayPosition | null }>(`/api/replay/markets/${marketId}`),
  buyShares: (marketId: number, quantity: number) =>
    post<ReplayBuyResponse>(`/api/replay/markets/${marketId}/buy`, { quantity }),
  sellShares: (marketId: number, quantity: number) =>
    post<ReplaySellResponse>(`/api/replay/markets/${marketId}/sell`, { quantity }),
  estimateCost: (marketId: number, quantity: number, side: 'buy' | 'sell') =>
    post<ReplayEstimateResponse>(`/api/replay/markets/${marketId}/estimate`, { quantity, side }),
  getPriceHistory: (marketId: number, limit = 100) =>
    get<{ market_id: number; history: ReplayPriceHistoryEntry[] }>(
      `/api/replay/markets/${marketId}/price-history`,
      { limit }
    ),

  // Portfolio & Wallet
  getPortfolio: () => get<{ positions: ReplayPosition[]; total_pnl: ReplayPnL }>('/api/replay/portfolio'),
  getWallet: () => get<{ balance: number; locked_balance: number }>('/api/replay/wallet'),
  getLedger: (limit = 100) => get<{ ledger: ReplayLedgerEntry[] }>('/api/replay/wallet/ledger', { limit }),

  // Race info
  getRaces: () => get<{ races: ReplayRace[] }>('/api/replay/races'),
  getRaceResults: (raceNumber: number) =>
    get<{
      race_number: number;
      name: string;
      venue: string;
      date: string;
      results: ReplayRaceResult[];
    }>(`/api/replay/races/${raceNumber}/results`),

  // Leaderboard
  getLeaderboard: (limit = 50, difficulty?: 'easy' | 'medium' | 'hard') =>
    get<ReplayLeaderboard>('/api/replay/leaderboard', { limit, ...(difficulty && { difficulty }) }),
};
