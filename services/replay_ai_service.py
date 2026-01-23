"""AI player service for replay competition.

This service manages AI players that provide competition on the leaderboard.
AI players simulate actual trading strategies using known F1 2024 race results.
Smarter AI (higher difficulty) makes bets based on actual race outcomes.

In timer mode, AI trades are scheduled at race start and executed lazily
throughout the trading window, affecting bonding curve prices in real-time.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Tuple, Optional
import random

from db import db
from db.replay_models import (
    ReplayAIPlayer, ReplayDifficulty, ReplayScheduledAITrade,
    ReplayMarket, ReplayPriceHistory
)
from db.models import utc_now
from data.f1_2024 import RACES_2024, get_points_for_position
from pricing.bonding_curve import price, buy_cost


# Cost per share at empty market (bonding curve: a=0.1, b=0.5)
# integral from 0 to 1 of (0.1*s + 0.5) = 0.55
COST_PER_SHARE = Decimal('0.55')

# Points to return multiplier (25 pts winner = 2.5x return, 0 pts = total loss)
# This normalizes returns to prevent astronomical compounding
POINTS_RETURN_DIVISOR = Decimal('10')

# Minimum balance to keep (don't go all-in)
MIN_RESERVE = Decimal('5.00')

# Default AI investment per race as fraction of current balance (overridden by difficulty)
DEFAULT_INVESTMENT_FRACTION = Decimal('0.10')

# Time slot distributions for AI trades per difficulty
# Format: list of (start_second, end_second, fraction_of_trades)
AI_TRADE_TIMING = {
    ReplayDifficulty.EASY: [
        (6, 8, 0.40),   # Late trades - user gets better prices
        (8, 10, 0.60),
    ],
    ReplayDifficulty.MEDIUM: [
        (2, 4, 0.25),
        (4, 6, 0.25),
        (6, 8, 0.25),
        (8, 10, 0.25),
    ],
    ReplayDifficulty.HARD: [
        (0, 2, 0.50),   # Early trades - AI gets better prices
        (2, 4, 0.30),
        (4, 6, 0.15),
        (6, 10, 0.05),
    ],
}


def _get_race_driver_points(race_number: int) -> Dict[str, int]:
    """Get points earned by each driver in a race.

    Args:
        race_number: Race number (1-24)

    Returns:
        Dict mapping driver_code to points earned
    """
    race = RACES_2024.get(race_number)
    if not race:
        return {}

    return {
        driver_code: int(get_points_for_position(position))
        for driver_code, position in race["results"]
    }


def _get_top_n_drivers(race_number: int, n: int) -> List[str]:
    """Get top N finishing drivers for a race.

    Args:
        race_number: Race number (1-24)
        n: Number of top drivers to return

    Returns:
        List of driver codes in finishing order
    """
    race = RACES_2024.get(race_number)
    if not race:
        return []

    # Filter out DNFs (position 0) and take top N
    finishers = [(code, pos) for code, pos in race["results"] if pos > 0]
    finishers.sort(key=lambda x: x[1])
    return [code for code, _ in finishers[:n]]


def _get_bottom_n_drivers(race_number: int, n: int) -> List[str]:
    """Get bottom N finishing drivers (worst performers including DNFs).

    Args:
        race_number: Race number (1-24)
        n: Number of bottom drivers to return

    Returns:
        List of driver codes (DNFs first, then worst finishers)
    """
    race = RACES_2024.get(race_number)
    if not race:
        return []

    # DNFs have position 0, treat as worst
    results = [(code, pos if pos > 0 else 100) for code, pos in race["results"]]
    results.sort(key=lambda x: x[1], reverse=True)
    return [code for code, _ in results[:n]]


def _get_midfield_drivers(race_number: int) -> List[str]:
    """Get midfield drivers (positions 6-12) for a race.

    Args:
        race_number: Race number (1-24)

    Returns:
        List of driver codes finishing P6-P12
    """
    race = RACES_2024.get(race_number)
    if not race:
        return []

    return [
        code for code, pos in race["results"]
        if 6 <= pos <= 12
    ]


# AI Strategy definitions
# Each strategy returns list of (driver_code, share_fraction) tuples
# share_fraction is how much of the investment goes to each driver

class AIStrategy:
    """Base class for AI trading strategies."""

    @staticmethod
    def get_picks(race_number: int, rng: random.Random) -> List[Tuple[str, float]]:
        """Get driver picks for a race.

        Args:
            race_number: Race number (1-24)
            rng: Random number generator for deterministic results

        Returns:
            List of (driver_code, allocation_fraction) tuples
        """
        raise NotImplementedError


class OracleStrategy(AIStrategy):
    """Perfect foresight - always bets on the race winner."""

    @staticmethod
    def get_picks(race_number: int, rng: random.Random) -> List[Tuple[str, float]]:
        winners = _get_top_n_drivers(race_number, 1)
        if winners:
            return [(winners[0], 1.0)]
        return []


class Top3Strategy(AIStrategy):
    """Bets on top 3 finishers - very good strategy."""

    @staticmethod
    def get_picks(race_number: int, rng: random.Random) -> List[Tuple[str, float]]:
        top3 = _get_top_n_drivers(race_number, 3)
        # Weight more heavily towards winner
        weights = [0.5, 0.3, 0.2]
        return [(driver, weights[i]) for i, driver in enumerate(top3)]


class PodiumPlusStrategy(AIStrategy):
    """Bets on top 5 finishers - good diversified strategy."""

    @staticmethod
    def get_picks(race_number: int, rng: random.Random) -> List[Tuple[str, float]]:
        top5 = _get_top_n_drivers(race_number, 5)
        # Even distribution
        weight = 1.0 / len(top5) if top5 else 0
        return [(driver, weight) for driver in top5]


class PointsScorerStrategy(AIStrategy):
    """Bets on drivers who score points (top 10) - moderate strategy."""

    @staticmethod
    def get_picks(race_number: int, rng: random.Random) -> List[Tuple[str, float]]:
        top10 = _get_top_n_drivers(race_number, 10)
        weight = 1.0 / len(top10) if top10 else 0
        return [(driver, weight) for driver in top10]


class MidfieldFanStrategy(AIStrategy):
    """Bets on midfield drivers (P6-P12) - modest returns."""

    @staticmethod
    def get_picks(race_number: int, rng: random.Random) -> List[Tuple[str, float]]:
        midfield = _get_midfield_drivers(race_number)
        if not midfield:
            return []
        weight = 1.0 / len(midfield)
        return [(driver, weight) for driver in midfield]


class RandomStrategy(AIStrategy):
    """Random picks - unpredictable results."""

    @staticmethod
    def get_picks(race_number: int, rng: random.Random) -> List[Tuple[str, float]]:
        race = RACES_2024.get(race_number)
        if not race:
            return []

        all_drivers = [code for code, _ in race["results"]]
        if not all_drivers:
            return []
        # Pick 3 random drivers
        picks = rng.sample(all_drivers, min(3, len(all_drivers)))
        if not picks:
            return []
        weight = 1.0 / len(picks)
        return [(driver, weight) for driver in picks]


class BackmarkerFanStrategy(AIStrategy):
    """Bets on worst finishers and DNFs - loses money consistently."""

    @staticmethod
    def get_picks(race_number: int, rng: random.Random) -> List[Tuple[str, float]]:
        bottom = _get_bottom_n_drivers(race_number, 5)
        if not bottom:
            return []
        weight = 1.0 / len(bottom)
        return [(driver, weight) for driver in bottom]


class ChaseHypeStrategy(AIStrategy):
    """Always bets on popular drivers regardless of results - poor timing."""
    FAVORITES = ["VER", "HAM", "LEC", "NOR"]  # Popular but not always winning

    @staticmethod
    def get_picks(race_number: int, rng: random.Random) -> List[Tuple[str, float]]:
        # Always bet on favorites even when they DNF
        weight = 1.0 / len(ChaseHypeStrategy.FAVORITES)
        return [(driver, weight) for driver in ChaseHypeStrategy.FAVORITES]


# Map strategy names to implementations
STRATEGIES = {
    "oracle": OracleStrategy,
    "top3_picker": Top3Strategy,
    "podium_plus": PodiumPlusStrategy,
    "points_scorer": PointsScorerStrategy,
    "midfield_fan": MidfieldFanStrategy,
    "random_trader": RandomStrategy,
    "backmarker_fan": BackmarkerFanStrategy,
    "chase_hype": ChaseHypeStrategy,
}


# AI Player configurations per difficulty level
# Each entry: (name, strategy_type, aggression)
# aggression: how much of balance to invest each race (multiplier of base)
AI_CONFIGS = {
    ReplayDifficulty.EASY: {
        "starting_balance": Decimal('100'),
        "investment_fraction": Decimal('0.08'),
        "players": [
            ("BackmarkerBot", "backmarker_fan", 0.8),
            ("BadTimingAI", "chase_hype", 0.6),
            ("RandomRick", "random_trader", 0.8),
            ("MidfieldMike", "midfield_fan", 0.7),
            ("CasualCarl", "points_scorer", 0.5),
        ]
    },
    ReplayDifficulty.MEDIUM: {
        "starting_balance": Decimal('150'),
        "investment_fraction": Decimal('0.12'),
        "players": [
            # Losing (3)
            ("BackmarkerBot", "backmarker_fan", 1.0),
            ("BadTimingAI", "chase_hype", 0.9),
            ("HypeChaser", "chase_hype", 1.0),
            # Breakeven (3)
            ("RandomRick", "random_trader", 1.0),
            ("RandomRachel", "random_trader", 0.9),
            ("MidfieldMike", "midfield_fan", 1.0),
            # Moderate (3)
            ("DiverseDan", "points_scorer", 1.1),
            ("ValueVic", "podium_plus", 1.0),
            ("TopPickerTom", "top3_picker", 1.0),
            # Strong (4)
            ("TopPickerTina", "top3_picker", 1.2),
            ("WinnerWill", "top3_picker", 1.3),
            ("ProTrader1", "oracle", 0.9),
            ("ProTrader2", "oracle", 1.1),
            # Champion (2)
            ("OracleAI", "oracle", 1.2),
            ("ChampionAI", "oracle", 1.4),
        ]  # 15 total
    },
    ReplayDifficulty.HARD: {
        "starting_balance": Decimal('200'),
        "investment_fraction": Decimal('0.18'),
        "players": [
            # Losing bots (5)
            ("BackmarkerBot1", "backmarker_fan", 1.2),
            ("BackmarkerBot2", "backmarker_fan", 1.3),
            ("BadTimingAI", "chase_hype", 1.2),
            ("HypeChaser1", "chase_hype", 1.4),
            ("HypeChaser2", "chase_hype", 1.5),
            # Breakeven bots (6)
            ("RandomRick", "random_trader", 1.2),
            ("RandomRachel", "random_trader", 1.3),
            ("RandomRob", "random_trader", 1.4),
            ("MidfieldMike", "midfield_fan", 1.2),
            ("MidfieldMary", "midfield_fan", 1.3),
            ("MidfieldMax", "midfield_fan", 1.4),
            # Moderate winners (6)
            ("DiverseDan", "points_scorer", 1.4),
            ("DiverseDiana", "points_scorer", 1.5),
            ("DiverseDave", "points_scorer", 1.6),
            ("ValueVic", "podium_plus", 1.4),
            ("ValueVera", "podium_plus", 1.5),
            ("ValueVince", "podium_plus", 1.6),
            # Strong competitors (10) - top3 strategies
            ("TopPickerTom", "top3_picker", 1.4),
            ("TopPickerTina", "top3_picker", 1.5),
            ("TopPickerTed", "top3_picker", 1.6),
            ("TopPickerTracy", "top3_picker", 1.7),
            ("WinnerWill", "top3_picker", 1.8),
            ("WinnerWanda", "top3_picker", 1.9),
            ("WinnerWade", "top3_picker", 2.0),
            ("WinnerWendy", "top3_picker", 2.1),
            ("EliteEric", "top3_picker", 2.2),
            ("EliteEva", "top3_picker", 2.3),
            # Oracle champions (8) - perfect foresight
            ("ProTrader1", "oracle", 1.5),
            ("ProTrader2", "oracle", 1.6),
            ("ProTrader3", "oracle", 1.7),
            ("ProTrader4", "oracle", 1.8),
            ("OracleAI1", "oracle", 2.0),
            ("OracleAI2", "oracle", 2.2),
            ("ChampionAI", "oracle", 2.3),
            ("GOAT_Trader", "oracle", 2.5),
        ]  # 35 total
    }
}


def _simulate_ai_season(
    strategy_type: str,
    aggression: float,
    seed: int,
    starting_balance: Decimal = Decimal('100'),
    investment_fraction: Decimal = DEFAULT_INVESTMENT_FRACTION
) -> List[Decimal]:
    """Simulate an AI player's balance through all 24 races.

    Args:
        strategy_type: Name of the strategy to use
        aggression: Multiplier for investment fraction
        seed: Random seed for deterministic results
        starting_balance: Initial balance for this AI
        investment_fraction: Base investment fraction per race

    Returns:
        List of 25 Decimals: balance after each race (index 0 = starting balance)
    """
    rng = random.Random(seed)
    strategy_class = STRATEGIES.get(strategy_type, RandomStrategy)

    balance = starting_balance
    balances = [balance]  # Index 0 = starting balance

    for race_num in range(1, 25):
        # Get race results for payout calculation
        driver_points = _get_race_driver_points(race_num)

        # Determine investment amount
        available = max(Decimal('0'), balance - MIN_RESERVE)
        investment = min(available, balance * investment_fraction * Decimal(str(aggression)))

        if investment <= 0:
            balances.append(balance)
            continue

        # Get picks from strategy
        picks = strategy_class.get_picks(race_num, rng)

        if not picks:
            balances.append(balance)
            continue

        # Execute trades
        total_payout = Decimal('0')
        total_cost = Decimal('0')

        for driver_code, allocation in picks:
            driver_investment = investment * Decimal(str(allocation))
            shares = driver_investment / COST_PER_SHARE
            cost = shares * COST_PER_SHARE

            # Get points earned by this driver
            # Normalize returns: 25 pts = 2.5x, 10 pts = 1x (breakeven), 0 pts = 0x (total loss)
            points = driver_points.get(driver_code, 0)
            return_multiplier = Decimal(str(points)) / POINTS_RETURN_DIVISOR
            payout = cost * return_multiplier

            total_cost += cost
            total_payout += payout

        # Update balance: subtract cost, add payout
        balance = balance - total_cost + total_payout
        balance = max(Decimal('0'), balance)  # Can't go negative
        balances.append(round(balance, 2))

    return balances


class ReplayAIService:
    """Service for managing AI players in replay mode."""

    # Cache for simulated AI balances: {(difficulty, name): [balances]}
    _balance_cache: Dict[Tuple[ReplayDifficulty, str], List[Decimal]] = {}

    @classmethod
    def _get_ai_balances(cls, difficulty: ReplayDifficulty, name: str,
                         strategy_type: str, aggression: float) -> List[Decimal]:
        """Get cached or compute AI balances for all 24 races.

        Args:
            difficulty: Difficulty level
            name: AI player name
            strategy_type: Strategy type
            aggression: Aggression multiplier

        Returns:
            List of 25 Decimals (starting balance + 24 race balances)
        """
        cache_key = (difficulty, name)
        if cache_key not in cls._balance_cache:
            # Get difficulty-specific settings
            config = AI_CONFIGS.get(difficulty, {})
            starting_balance = config.get("starting_balance", Decimal('100'))
            investment_fraction = config.get("investment_fraction", DEFAULT_INVESTMENT_FRACTION)

            # Use name as seed for deterministic results per AI
            seed = hash(name) % (2**31)
            cls._balance_cache[cache_key] = _simulate_ai_season(
                strategy_type, aggression, seed,
                starting_balance=starting_balance,
                investment_fraction=investment_fraction
            )
        return cls._balance_cache[cache_key]

    @classmethod
    def clear_cache(cls):
        """Clear the balance cache (useful for testing)."""
        cls._balance_cache.clear()

    @staticmethod
    def initialize_ai_players(seed: int = 42) -> Dict[str, int]:
        """Initialize AI players for all difficulty levels.

        Computes final balances by simulating the full season.

        Args:
            seed: Random seed (unused, kept for API compatibility)

        Returns:
            Dict with counts per difficulty level
        """
        counts = {}

        # Clear cache to ensure fresh simulation
        ReplayAIService.clear_cache()

        for difficulty, config in AI_CONFIGS.items():
            # Clear existing AI players for this difficulty
            ReplayAIPlayer.query.filter_by(difficulty=difficulty).delete(synchronize_session=False)

            created = 0
            for name, strategy_type, aggression in config["players"]:
                # Simulate full season to get final balance
                balances = ReplayAIService._get_ai_balances(
                    difficulty, name, strategy_type, aggression
                )
                final_balance = balances[-1]  # Balance after race 24

                player = ReplayAIPlayer(
                    name=name,
                    difficulty=difficulty,
                    final_balance=final_balance,
                    strategy_type=strategy_type
                )
                db.session.add(player)
                created += 1

            counts[difficulty.value] = created

        db.session.commit()
        return counts

    @staticmethod
    def get_ai_players(difficulty: ReplayDifficulty) -> List[Dict]:
        """Get all AI players for a difficulty level.

        Args:
            difficulty: The difficulty level

        Returns:
            List of AI player dicts with leaderboard-compatible format
        """
        players = ReplayAIPlayer.query.filter_by(
            difficulty=difficulty
        ).order_by(ReplayAIPlayer.final_balance.desc()).all()

        return [
            {
                "name": player.name,
                "final_balance": float(player.final_balance),
                "strategy_type": player.strategy_type,
                "is_ai": True
            }
            for player in players
        ]

    @staticmethod
    def ensure_ai_players_exist() -> bool:
        """Ensure AI players exist in the database.

        Also reinitializes if the config has changed (different player count).

        Returns:
            True if AI players were created/updated, False if they already existed
        """
        needs_init = False

        # Check if any AI players exist
        total_count = ReplayAIPlayer.query.count()
        if total_count == 0:
            needs_init = True
        else:
            # Check if counts match expected config for each difficulty
            for difficulty, config in AI_CONFIGS.items():
                expected_count = len(config["players"])
                actual_count = ReplayAIPlayer.query.filter_by(difficulty=difficulty).count()
                if actual_count != expected_count:
                    needs_init = True
                    break

        if needs_init:
            ReplayAIService.initialize_ai_players()
            return True
        return False

    @staticmethod
    def get_ai_player_count() -> Dict[str, int]:
        """Get count of AI players per difficulty.

        Returns:
            Dict mapping difficulty to count
        """
        counts = {}
        for difficulty in ReplayDifficulty:
            count = ReplayAIPlayer.query.filter_by(difficulty=difficulty).count()
            counts[difficulty.value] = count
        return counts

    @staticmethod
    def get_ai_standings_at_race(difficulty: ReplayDifficulty, race_number: int) -> List[Dict]:
        """Get AI player standings at a specific race.

        Uses simulated trading to calculate actual balance at each race,
        based on the AI's strategy and the known race results.

        Args:
            difficulty: Difficulty level to filter AI players
            race_number: Race number (1-24)

        Returns:
            List of AI players with actual simulated balances, sorted by balance desc
        """
        config = AI_CONFIGS.get(difficulty, {"players": []})

        standings = []
        for name, strategy_type, aggression in config["players"]:
            # Get simulated balances for this AI
            balances = ReplayAIService._get_ai_balances(
                difficulty, name, strategy_type, aggression
            )

            # Get balance at the specified race
            # race_number 1-24 maps to index 1-24 in balances array
            balance_at_race = float(balances[min(race_number, 24)])

            standings.append({
                "name": name,
                "balance": round(balance_at_race, 2),
                "is_ai": True
            })

        # Sort by balance descending
        standings.sort(key=lambda x: x["balance"], reverse=True)
        return standings

    @staticmethod
    def reinitialize_ai_players() -> Dict[str, int]:
        """Force re-initialization of AI players.

        Useful when strategy logic changes.

        Returns:
            Dict with counts per difficulty level
        """
        return ReplayAIService.initialize_ai_players()

    @staticmethod
    def schedule_ai_trades_for_race(
        session_id: int,
        race_number: int,
        market_opens_at: datetime,
        duration_seconds: int,
        difficulty: ReplayDifficulty
    ) -> List[ReplayScheduledAITrade]:
        """Schedule AI trades across the market window.

        Distributes trades into time slots based on difficulty:
        - EASY: AI trades late, user gets better prices
        - MEDIUM: AI trades evenly distributed
        - HARD: AI trades early, gets better prices

        Args:
            session_id: The replay session ID
            race_number: Current race number (1-24)
            market_opens_at: When the market opens
            duration_seconds: Total trading window duration
            difficulty: Difficulty level for timing distribution

        Returns:
            List of scheduled AI trades
        """
        config = AI_CONFIGS.get(difficulty, AI_CONFIGS[ReplayDifficulty.MEDIUM])
        timing_slots = AI_TRADE_TIMING.get(difficulty, AI_TRADE_TIMING[ReplayDifficulty.MEDIUM])

        starting_balance = config.get("starting_balance", Decimal('100'))
        investment_fraction = config.get("investment_fraction", DEFAULT_INVESTMENT_FRACTION)

        # Get markets for this race
        markets = ReplayMarket.query.filter_by(
            session_id=session_id,
            race_number=race_number
        ).all()
        market_by_driver = {m.driver_code: m for m in markets}

        scheduled_trades = []
        rng = random.Random(42 + session_id + race_number)  # Deterministic per session/race

        for name, strategy_type, aggression in config["players"]:
            strategy_class = STRATEGIES.get(strategy_type, RandomStrategy)

            # Get AI's current simulated balance at this race
            # We use the pre-race balance (race_number - 1 index, but min 0)
            balances = ReplayAIService._get_ai_balances(
                difficulty, name, strategy_type, aggression
            )
            balance_index = max(0, race_number - 1)
            current_balance = balances[balance_index]

            # Calculate investment for this race
            available = max(Decimal('0'), current_balance - MIN_RESERVE)
            investment = min(
                available,
                current_balance * investment_fraction * Decimal(str(aggression))
            )

            if investment <= Decimal('0'):
                continue

            # Get strategy picks
            picks = strategy_class.get_picks(race_number, rng)
            if not picks:
                continue

            # Distribute this AI's trades across time slots
            # For simplicity, put all trades in a random slot based on timing distribution
            slot_rand = rng.random()
            cumulative = 0.0
            chosen_start, chosen_end = timing_slots[0][0], timing_slots[0][1]

            for start_sec, end_sec, fraction in timing_slots:
                cumulative += fraction
                if slot_rand <= cumulative:
                    chosen_start, chosen_end = start_sec, end_sec
                    break

            # Random time within the chosen slot
            trade_offset = rng.uniform(chosen_start, chosen_end)
            scheduled_time = market_opens_at + timedelta(seconds=trade_offset)

            # Create scheduled trades for each driver pick
            for driver_code, allocation in picks:
                market = market_by_driver.get(driver_code)
                if not market:
                    continue

                driver_investment = investment * Decimal(str(allocation))
                # Estimate shares at baseline price (will recalculate at execution)
                shares = driver_investment / COST_PER_SHARE

                if shares <= Decimal('0'):
                    continue

                trade = ReplayScheduledAITrade(
                    session_id=session_id,
                    market_id=market.id,
                    ai_player_name=name,
                    quantity=shares,
                    scheduled_at=scheduled_time,
                    executed_at=None,
                    execution_price=None,
                    execution_cost=None
                )
                db.session.add(trade)
                scheduled_trades.append(trade)

        db.session.flush()
        return scheduled_trades

    @staticmethod
    def execute_pending_ai_trades(
        session_id: int,
        up_to_time: Optional[datetime] = None
    ) -> List[Dict]:
        """Execute all scheduled AI trades that should have happened by now.

        Uses lazy execution - trades are executed in order when polled.

        Args:
            session_id: The replay session ID
            up_to_time: Execute trades scheduled before this time (default: now)

        Returns:
            List of executed trade details with price impacts
        """
        if up_to_time is None:
            up_to_time = utc_now()

        # Get pending trades scheduled before up_to_time, ordered by time
        pending_trades = ReplayScheduledAITrade.query.filter(
            ReplayScheduledAITrade.session_id == session_id,
            ReplayScheduledAITrade.scheduled_at <= up_to_time,
            ReplayScheduledAITrade.executed_at.is_(None)
        ).order_by(ReplayScheduledAITrade.scheduled_at).with_for_update().all()

        executed = []

        for trade in pending_trades:
            market = ReplayMarket.query.get(trade.market_id)
            if not market or market.status.value != 'open':
                # Mark as executed but skip (market closed or doesn't exist)
                trade.executed_at = utc_now()
                trade.execution_price = Decimal('0')
                trade.execution_cost = Decimal('0')
                continue

            # Get current supply from positions
            from services.replay_market_service import ReplayMarketService
            current_supply = ReplayMarketService.get_current_supply(trade.market_id)

            # Calculate cost using bonding curve
            a = Decimal(str(market.a))
            b = Decimal(str(market.b))
            quantity = trade.quantity

            cost = buy_cost(current_supply, quantity, a, b)
            new_supply = current_supply + quantity
            new_price = price(new_supply, a, b)

            # Record the trade execution
            trade.executed_at = utc_now()
            trade.execution_price = new_price
            trade.execution_cost = cost

            # Update price history
            price_entry = ReplayPriceHistory(
                market_id=trade.market_id,
                timestamp=utc_now(),
                price=new_price,
                supply=new_supply,
                reason=f"ai_buy_{trade.ai_player_name}"
            )
            db.session.add(price_entry)

            executed.append({
                "ai_player": trade.ai_player_name,
                "market_id": trade.market_id,
                "driver_code": market.driver_code,
                "quantity": float(quantity),
                "cost": float(cost),
                "new_price": float(new_price),
                "new_supply": float(new_supply)
            })

        if executed:
            db.session.flush()

        return executed

    @staticmethod
    def get_pending_ai_trade_count(session_id: int) -> int:
        """Get count of pending AI trades for a session.

        Args:
            session_id: The replay session ID

        Returns:
            Number of pending trades
        """
        return ReplayScheduledAITrade.query.filter(
            ReplayScheduledAITrade.session_id == session_id,
            ReplayScheduledAITrade.executed_at.is_(None)
        ).count()

    @staticmethod
    def clear_scheduled_trades(session_id: int) -> int:
        """Clear all scheduled AI trades for a session.

        Called when resetting a session.

        Args:
            session_id: The replay session ID

        Returns:
            Number of trades deleted
        """
        count = ReplayScheduledAITrade.query.filter_by(session_id=session_id).delete()
        db.session.flush()
        return count
