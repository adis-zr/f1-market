"""AI player service for replay competition.

This service manages AI players that provide competition on the leaderboard.
AI players simulate actual trading strategies using known F1 2024 race results.
Smarter AI (higher difficulty) makes bets based on actual race outcomes.
"""
from decimal import Decimal
from typing import List, Dict, Tuple
import random

from db import db
from db.replay_models import ReplayAIPlayer, ReplayDifficulty
from data.f1_2024 import RACES_2024, get_points_for_position


# Cost per share at empty market (bonding curve: a=0.1, b=0.5)
# integral from 0 to 1 of (0.1*s + 0.5) = 0.55
COST_PER_SHARE = Decimal('0.55')

# AI investment per race as fraction of current balance
INVESTMENT_FRACTION = Decimal('0.15')

# Minimum balance to keep (don't go all-in)
MIN_RESERVE = Decimal('5.00')


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
        "players": [
            ("BackmarkerBot", "backmarker_fan", 1.0),
            ("BadTimingAI", "chase_hype", 0.8),
            ("HypeChaser", "chase_hype", 1.2),
            ("RandomRick", "random_trader", 1.0),
            ("DiverseDan", "points_scorer", 0.5),  # Too conservative
        ]
    },
    ReplayDifficulty.MEDIUM: {
        "players": [
            # Losing bots
            ("BackmarkerBot", "backmarker_fan", 1.0),
            ("BadTimingAI", "chase_hype", 0.8),
            # Breakeven bots
            ("RandomRick", "random_trader", 1.0),
            ("RandomRachel", "random_trader", 0.8),
            ("MidfieldMike", "midfield_fan", 1.0),
            # Moderate winners
            ("DiverseDan", "points_scorer", 1.0),
            ("DiverseDiana", "points_scorer", 1.2),
            # Good bots
            ("ValueVic", "podium_plus", 1.0),
            ("TopPickerTom", "top3_picker", 0.8),
            ("WinnerWill", "top3_picker", 1.2),
        ]
    },
    ReplayDifficulty.HARD: {
        "players": [
            # Losing bots (4)
            ("BackmarkerBot", "backmarker_fan", 1.0),
            ("BadTimingAI", "chase_hype", 1.0),
            ("HypeChaser1", "chase_hype", 0.8),
            ("HypeChaser2", "backmarker_fan", 0.8),
            # Breakeven bots (4)
            ("RandomRick", "random_trader", 1.0),
            ("RandomRachel", "random_trader", 0.8),
            ("MidfieldMike", "midfield_fan", 1.0),
            ("MidfieldMary", "midfield_fan", 1.2),
            # Moderate winners (4)
            ("DiverseDan", "points_scorer", 1.0),
            ("DiverseDiana", "points_scorer", 1.2),
            ("ValueVic", "podium_plus", 1.0),
            ("ValueVera", "podium_plus", 1.2),
            # Strong competitors (6)
            ("TopPickerTom", "top3_picker", 1.0),
            ("TopPickerTina", "top3_picker", 1.2),
            ("WinnerWill", "top3_picker", 1.4),
            ("WinnerWanda", "top3_picker", 1.3),
            ("ProTrader1", "oracle", 0.8),  # Conservative oracle
            ("ProTrader2", "oracle", 1.0),
            # Champion (2)
            ("OracleAI", "oracle", 1.2),
            ("ChampionAI", "oracle", 1.5),  # Aggressive oracle
        ]
    }
}


def _simulate_ai_season(strategy_type: str, aggression: float, seed: int) -> List[Decimal]:
    """Simulate an AI player's balance through all 24 races.

    Args:
        strategy_type: Name of the strategy to use
        aggression: Multiplier for investment fraction
        seed: Random seed for deterministic results

    Returns:
        List of 25 Decimals: balance after each race (index 0 = starting balance)
    """
    rng = random.Random(seed)
    strategy_class = STRATEGIES.get(strategy_type, RandomStrategy)

    balance = Decimal('100.00')
    balances = [balance]  # Index 0 = starting balance ($100)

    for race_num in range(1, 25):
        # Get race results for payout calculation
        driver_points = _get_race_driver_points(race_num)

        # Determine investment amount
        available = max(Decimal('0'), balance - MIN_RESERVE)
        investment = min(available, balance * INVESTMENT_FRACTION * Decimal(str(aggression)))

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
            points = driver_points.get(driver_code, 0)
            payout = shares * Decimal(str(points))

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
            # Use name as seed for deterministic results per AI
            seed = hash(name) % (2**31)
            cls._balance_cache[cache_key] = _simulate_ai_season(
                strategy_type, aggression, seed
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
