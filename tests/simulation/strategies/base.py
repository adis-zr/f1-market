"""Base trading strategy class."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Tuple


@dataclass
class TradeAction:
    """Represents a single trade action."""
    driver_code: str
    action: str  # "buy" or "sell"
    quantity: Decimal

    def __repr__(self) -> str:
        return f"TradeAction({self.action} {self.quantity} of {self.driver_code})"


class TradingStrategy(ABC):
    """Abstract base class for trading strategies.

    Each strategy determines what trades to make for a given race
    based on the race results, current positions, and wallet balance.
    """

    def __init__(self, user_id: int, name: str):
        """Initialize the trading strategy.

        Args:
            user_id: The user ID this strategy is for
            name: Human-readable strategy name
        """
        self.user_id = user_id
        self.name = name

    @abstractmethod
    def get_trades(
        self,
        race_num: int,
        race_results: List[Tuple[str, int]],
        current_positions: Dict[str, Decimal],
        wallet_balance: Decimal,
    ) -> List[TradeAction]:
        """Determine trades to make for a race.

        Args:
            race_num: Race number (1-24)
            race_results: List of (driver_code, position) for this race
            current_positions: Dict of driver_code -> shares held
            wallet_balance: Current available wallet balance

        Returns:
            List of TradeAction objects
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(user_id={self.user_id}, name='{self.name}')"
