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

// Auth endpoints
export const authApi = {
  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },
  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout');
  },
};

// Sports & Leagues endpoints
export const sportsApi = {
  getSports: async (): Promise<Sport[]> => {
    const response = await apiClient.get('/api/sports');
    return response.data;
  },
  getLeagues: async (sportId?: number): Promise<League[]> => {
    const params = sportId ? { sport_id: sportId } : {};
    const response = await apiClient.get('/api/leagues', { params });
    return response.data;
  },
  getSeasons: async (leagueId?: number): Promise<Season[]> => {
    const params = leagueId ? { league_id: leagueId } : {};
    const response = await apiClient.get('/api/seasons', { params });
    return response.data;
  },
};

// Events endpoints
export const eventsApi = {
  getEvents: async (filters?: {
    sport_id?: number;
    season_id?: number;
    status?: string;
  }): Promise<Event[]> => {
    const response = await apiClient.get('/api/events', { params: filters });
    return response.data;
  },
  getEvent: async (eventId: number): Promise<Event> => {
    const response = await apiClient.get(`/api/events/${eventId}`);
    return response.data;
  },
  getEventMarkets: async (eventId: number): Promise<Market[]> => {
    const response = await apiClient.get(`/api/events/${eventId}/markets`);
    return response.data;
  },
  getEventResults: async (eventId: number): Promise<EventResult[]> => {
    const response = await apiClient.get(`/api/events/${eventId}/results`);
    return response.data;
  },
};

// Markets endpoints
export const marketsApi = {
  getMarkets: async (filters?: {
    event_id?: number;
    sport_id?: number;
    status?: string;
  }): Promise<Market[]> => {
    const response = await apiClient.get('/api/markets', { params: filters });
    return response.data;
  },
  getMarket: async (marketId: number): Promise<Market> => {
    const response = await apiClient.get(`/api/markets/${marketId}`);
    return response.data;
  },
  getPriceHistory: async (marketId: number, limit = 100): Promise<PriceHistory> => {
    const response = await apiClient.get(`/api/markets/${marketId}/price-history`, {
      params: { limit },
    });
    return response.data;
  },
  getPosition: async (marketId: number): Promise<Position> => {
    const response = await apiClient.get(`/api/markets/${marketId}/positions`);
    return response.data;
  },
  buyShares: async (marketId: number, data: BuySharesRequest): Promise<BuySharesResponse> => {
    const response = await apiClient.post(`/api/markets/${marketId}/buy`, data);
    return response.data;
  },
  sellShares: async (marketId: number, data: SellSharesRequest): Promise<SellSharesResponse> => {
    const response = await apiClient.post(`/api/markets/${marketId}/sell`, data);
    return response.data;
  },
  getWallet: async (marketId: number): Promise<Wallet> => {
    const response = await apiClient.get(`/api/markets/${marketId}/wallet`);
    return response.data;
  },
};

// Portfolio & Wallet endpoints
export const portfolioApi = {
  getPortfolio: async (): Promise<Position[]> => {
    const response = await apiClient.get('/api/portfolio');
    return response.data;
  },
  getWallet: async (): Promise<Wallet> => {
    const response = await apiClient.get('/api/wallet');
    return response.data;
  },
  getLedger: async (params?: { limit?: number; type?: string }): Promise<LedgerEntry[]> => {
    const response = await apiClient.get('/api/wallet/ledger', { params });
    return response.data;
  },
};

