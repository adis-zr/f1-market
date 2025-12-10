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
};

// Portfolio & Wallet
export const portfolioApi = {
  getPortfolio: () => get<Position[]>('/api/portfolio'),
  getWallet: () => get<Wallet>('/api/wallet'),
  getLedger: (params?: { limit?: number; type?: string }) => get<LedgerEntry[]>('/api/wallet/ledger', params),
};
