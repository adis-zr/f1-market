"""AI player service for replay competition.

This service manages AI players that provide competition on the leaderboard.
AI player results are pre-computed based on trading strategy performance.
"""
from decimal import Decimal
from typing import List, Dict
import random

from db import db
from db.replay_models import ReplayAIPlayer, ReplayDifficulty


# AI Player configurations per difficulty level
# Each entry: (name_prefix, strategy_type, balance_range_low, balance_range_high)
AI_CONFIGS = {
    ReplayDifficulty.EASY: {
        "count": 5,
        "players": [
            ("BackmarkerBot", "backmarker_fan", Decimal('45'), Decimal('65')),
            ("BadTimingAI", "bad_timing", Decimal('50'), Decimal('70')),
            ("HypeChaser", "chase_hype", Decimal('55'), Decimal('75')),
            ("RandomRick", "random_trader", Decimal('70'), Decimal('95')),
            ("DiverseDan", "diversified", Decimal('80'), Decimal('105')),
        ]
    },
    ReplayDifficulty.MEDIUM: {
        "count": 10,
        "players": [
            ("BackmarkerBot", "backmarker_fan", Decimal('45'), Decimal('65')),
            ("BadTimingAI", "bad_timing", Decimal('50'), Decimal('70')),
            ("HypeChaser", "chase_hype", Decimal('55'), Decimal('75')),
            ("RandomRick", "random_trader", Decimal('70'), Decimal('95')),
            ("RandomRachel", "random_trader", Decimal('75'), Decimal('100')),
            ("DiverseDan", "diversified", Decimal('85'), Decimal('110')),
            ("DiverseDiana", "diversified", Decimal('90'), Decimal('115')),
            ("ValueVic", "value_hunter", Decimal('110'), Decimal('140')),
            ("MomentumMike", "momentum_trader", Decimal('115'), Decimal('145')),
            ("WinnerWill", "winner_predictor", Decimal('130'), Decimal('160')),
        ]
    },
    ReplayDifficulty.HARD: {
        "count": 20,
        "players": [
            # 4 losing bots (for some easy beats)
            ("BackmarkerBot", "backmarker_fan", Decimal('45'), Decimal('65')),
            ("BadTimingAI", "bad_timing", Decimal('55'), Decimal('75')),
            ("HypeChaser1", "chase_hype", Decimal('60'), Decimal('80')),
            ("HypeChaser2", "chase_hype", Decimal('65'), Decimal('85')),
            # 4 breakeven bots
            ("RandomRick", "random_trader", Decimal('80'), Decimal('105')),
            ("RandomRachel", "random_trader", Decimal('85'), Decimal('110')),
            ("DiverseDan", "diversified", Decimal('90'), Decimal('115')),
            ("DiverseDiana", "diversified", Decimal('95'), Decimal('120')),
            # 12 profitable bots (the real competition)
            ("ValueVic", "value_hunter", Decimal('115'), Decimal('145')),
            ("ValueVera", "value_hunter", Decimal('120'), Decimal('150')),
            ("ValueVince", "value_hunter", Decimal('125'), Decimal('155')),
            ("MomentumMike", "momentum_trader", Decimal('130'), Decimal('160')),
            ("MomentumMary", "momentum_trader", Decimal('135'), Decimal('165')),
            ("MomentumMax", "momentum_trader", Decimal('140'), Decimal('170')),
            ("WinnerWill", "winner_predictor", Decimal('145'), Decimal('175')),
            ("WinnerWanda", "winner_predictor", Decimal('150'), Decimal('180')),
            ("WinnerWayne", "winner_predictor", Decimal('155'), Decimal('185')),
            ("ProTrader1", "winner_predictor", Decimal('160'), Decimal('190')),
            ("ProTrader2", "value_hunter", Decimal('165'), Decimal('195')),
            ("ChampionAI", "winner_predictor", Decimal('180'), Decimal('220')),
        ]
    }
}


class ReplayAIService:
    """Service for managing AI players in replay mode."""

    @staticmethod
    def initialize_ai_players(seed: int = 42) -> Dict[str, int]:
        """Initialize AI players for all difficulty levels.

        Uses a deterministic seed for reproducible results.

        Args:
            seed: Random seed for reproducible balance generation

        Returns:
            Dict with counts per difficulty level
        """
        rng = random.Random(seed)
        counts = {}

        for difficulty, config in AI_CONFIGS.items():
            # Clear existing AI players for this difficulty
            ReplayAIPlayer.query.filter_by(difficulty=difficulty).delete()

            created = 0
            for name, strategy_type, balance_low, balance_high in config["players"]:
                # Generate deterministic balance within range
                balance_range = float(balance_high - balance_low)
                final_balance = balance_low + Decimal(str(round(rng.random() * balance_range, 2)))

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

        Returns:
            True if AI players were created, False if they already existed
        """
        # Check if any AI players exist
        count = ReplayAIPlayer.query.count()
        if count == 0:
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
        """Get AI player standings interpolated to a specific race.

        Uses linear interpolation to estimate AI balance at a given race:
        balance_at_race = $100 + (final_balance - $100) * (race_number / 24)

        Args:
            difficulty: Difficulty level to filter AI players
            race_number: Race number (1-24)

        Returns:
            List of AI players with interpolated balances, sorted by balance desc
        """
        players = ReplayAIPlayer.query.filter_by(difficulty=difficulty).all()

        standings = []
        for player in players:
            final = float(player.final_balance)
            # Linear interpolation from $100 to final_balance over 24 races
            interpolated_balance = 100 + (final - 100) * (race_number / 24)
            standings.append({
                "name": player.name,
                "balance": round(interpolated_balance, 2),
                "is_ai": True
            })

        # Sort by balance descending
        standings.sort(key=lambda x: x["balance"], reverse=True)
        return standings
