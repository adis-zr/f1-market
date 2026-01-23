// Core entities matching backend models

// API Error Response
export interface ApiError {
  error?: string;
  message?: string;
}

// Type guard to safely check if an error is an ApiError
export function isApiError(error: unknown): error is { response: { data: ApiError } } {
  return (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof (error as { response?: unknown }).response === 'object' &&
    (error as { response?: unknown }).response !== null &&
    'data' in (error as { response: { data?: unknown } }).response &&
    typeof (error as { response: { data?: unknown } }).response.data === 'object' &&
    (error as { response: { data?: unknown } }).response.data !== null
  );
}

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
  metadata_json: Record<string, unknown> | null;
}

export interface Team {
  id: number;
  sport_id: number;
  name: string;
  short_code: string | null;
  metadata_json: Record<string, unknown> | null;
}

export interface Event {
  id: number;
  season_id: number;
  name: string;
  venue: string | null;
  start_at: string | null;
  end_at: string | null;
  status: 'upcoming' | 'live' | 'finished';
  metadata: Record<string, unknown> | null;
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

// =============================================================================
// Replay Mode Types
// =============================================================================

export interface ReplaySession {
  session_id: number;
  user_id: number;
  current_race: number; // 0-24
  status: 'active' | 'completed' | 'abandoned';
  difficulty: ReplayDifficulty;
  started_at: string | null;
  completed_at: string | null;
  final_balance: number | null;
}

export type ReplayDifficulty = 'easy' | 'medium' | 'hard';

export interface ReplayWallet {
  balance: number;
  locked_balance: number;
}

export interface ReplayRace {
  race_number: number;
  name: string;
  venue: string;
  date: string;
  status: 'upcoming' | 'current' | 'completed';
}

export interface ReplayMarket {
  market_id: number;
  race_number: number;
  driver_code: string;
  driver_name: string;
  team_name: string | null;
  status: 'open' | 'closed' | 'settled';
  current_price: number;
  current_supply: number;
  settlement_price: number | null;
  payout_per_share: number | null;
}

export interface ReplayPosition {
  position_id: number;
  market_id: number;
  driver_code: string;
  driver_name: string;
  race_number: number;
  shares: number;
  avg_entry_price: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  realized_pnl: number;
  is_settled: boolean;
  can_sell: boolean;
}

export interface ReplayPnL {
  realized: number;
  unrealized: number;
  total: number;
}

export interface MarketTiming {
  opens_at: string | null;
  closes_at?: string | null;
  duration_seconds: number;
  server_time: string;
  time_remaining: number;
  can_trade: boolean;
  market_phase: 'pending' | 'open' | 'closed';
}

export interface ReplayState {
  session: ReplaySession;
  wallet: ReplayWallet;
  current_race_info: ReplayRace | null;
  markets: ReplayMarket[];
  positions: ReplayPosition[];
  total_pnl: ReplayPnL;
  all_races: ReplayRace[];
  market_timing: MarketTiming;
}

export interface ReplayRaceResult {
  driver_code: string;
  driver_name: string;
  team: string | null;
  position: number;
  points: number;
}

export interface ReplaySettledPosition {
  driver_code: string;
  shares: number;
  settlement_value: number;
  points_per_share: number;
}

export interface MiniLeaderboardEntry {
  rank: number;
  name: string;
  balance: number;
  is_ai: boolean;
}

export interface MiniLeaderboard {
  user_rank: number;
  user_balance: number;
  total_players: number;
  entries: MiniLeaderboardEntry[];
}

export interface ReplaySettlementSummary {
  race_number: number;
  race_name: string;
  results: Array<{
    driver_code: string;
    driver_name: string;
    position: number;
    points: number;
    payout_per_share: number;
  }>;
  your_settled_positions: ReplaySettledPosition[];
  total_settled_value: number;
  mini_leaderboard: MiniLeaderboard;
}

export interface ReplayAdvanceResponse {
  settlement_summary: ReplaySettlementSummary | null;
  new_state: ReplayState;
}

export interface ReplayBuyResponse {
  success: boolean;
  market_id: number;
  driver_code: string;
  quantity: number;
  cost: number;
  price_per_share: number;
  new_supply: number;
  new_price: number;
  position_shares: number;
  new_balance: number;
  trade_id: number;
}

export interface ReplaySellResponse {
  success: boolean;
  market_id: number;
  driver_code: string;
  quantity: number;
  payout: number;
  price_per_share: number;
  realized_pnl: number;
  new_supply: number;
  new_price: number;
  remaining_shares: number;
  new_balance: number;
  trade_id: number;
}

export interface ReplayEstimateResponse {
  side: 'buy' | 'sell';
  quantity: number;
  cost?: number;
  payout?: number;
  price_per_share: number;
  current_supply: number;
  new_supply: number;
  current_price: number;
  new_price: number;
}

export interface ReplayLeaderboardEntry {
  rank: number;
  username: string;
  user_id: number | null;
  is_ai: boolean;
  final_balance: number;
  return_pct: number;
  difficulty: ReplayDifficulty;
  completed_at: string | null;
}

export interface ReplayLeaderboard {
  entries: ReplayLeaderboardEntry[];
  your_best: {
    rank: number;
    final_balance: number;
    return_pct: number;
    difficulty: ReplayDifficulty;
    completed_at: string | null;
  } | null;
}

export interface ReplayPriceHistoryEntry {
  timestamp: string;
  price: number;
  supply: number;
  reason: string | null;
}

export interface ReplayLedgerEntry {
  id: number;
  amount: number;
  transaction_type: 'deposit' | 'withdrawal' | 'buy' | 'sell' | 'settlement' | 'fee';
  description: string | null;
  created_at: string | null;
}

