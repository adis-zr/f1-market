// Core entities matching backend models

export interface Sport {
  id: number;
  code: string;
  name: string;
}

export interface League {
  id: number;
  sport_id: number;
  name: string;
}

export interface Season {
  id: number;
  league_id: number;
  year: number;
  status: 'upcoming' | 'active' | 'finished';
}

export interface Participant {
  id: number;
  sport_id: number;
  name: string;
  short_code: string | null;
  metadata_json: Record<string, any> | null;
}

export interface Team {
  id: number;
  sport_id: number;
  name: string;
  short_code: string | null;
  metadata_json: Record<string, any> | null;
}

export interface Event {
  id: number;
  season_id: number;
  name: string;
  venue: string | null;
  start_at: string | null;
  end_at: string | null;
  status: 'upcoming' | 'live' | 'finished';
  metadata: Record<string, any> | null;
}

export interface Asset {
  id: number;
  type: 'participant' | 'team' | 'prop';
  symbol: string;
  display_name: string;
  participant?: Participant;
  team?: Team;
}

export interface Market {
  market_id: number;
  event_id: number;
  asset_id: number;
  status: 'open' | 'closed' | 'settled';
  current_price: number;
  current_supply: number;
  market_type: string;
  bonding_curve_a?: number;
  bonding_curve_b?: number;
  created_at?: string;
  updated_at?: string;
  // Include related data from joins
  asset?: Asset;
  event?: Event;
}

export interface Position {
  position_id: number;
  market_id: number;
  shares: number;
  avg_entry_price: number;
  realized_pnl: number;
  current_price: number | null;
  unrealized_pnl: number | null;
  total_pnl: number;
  last_marked_at?: string | null;
}

export interface Wallet {
  user_id: number;
  available_balance: number;
  total_balance: number;
  locked_balance: number;
}

export interface LedgerEntry {
  id: number;
  amount: number;
  transaction_type: 'deposit' | 'withdrawal' | 'buy' | 'sell' | 'settlement' | 'fee';
  reference_type: string | null;
  reference_id: number | null;
  description: string | null;
  created_at: string;
}

export interface EventResult {
  id: number;
  event_id: number;
  participant_id: number;
  primary_score: number;
  rank: number | null;
  status: 'finished' | 'dnf' | 'disqualified';
  participant?: Participant;
}

export interface PriceHistoryEntry {
  timestamp: string;
  price: number;
  reason: string | null;
}

export interface PriceHistory {
  market_id: number;
  history: PriceHistoryEntry[];
}

export interface User {
  email: string;
  username: string;
  role: string;
  logged_in: boolean;
}

export interface BuySharesRequest {
  quantity: number;
}

export interface SellSharesRequest {
  quantity: number;
}

export interface BuySharesResponse {
  success: boolean;
  market_id: number;
  quantity: number;
  cost: number;
  price_per_share: number;
  new_supply: number;
  new_price: number;
  position_shares: number;
  trade_id: number;
}

export interface SellSharesResponse {
  success: boolean;
  market_id: number;
  quantity: number;
  payout: number;
  price_per_share: number;
  realized_pnl: number;
  new_supply: number;
  new_price: number;
  remaining_shares: number;
  trade_id: number;
}

