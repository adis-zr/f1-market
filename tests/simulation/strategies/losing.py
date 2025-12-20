"""Losing trading strategies.

These strategies are designed to lose money by making poor decisions:
buying backmarkers, bad timing, or chasing past performance.
"""
from decimal import Decimal
from typing import Dict, List, Tuple, Optional

from .base import TradingStrategy, TradeAction


class BackmarkerFanStrategy(TradingStrategy):
    """Strategy: Always buy backmarker team drivers.

    These drivers rarely score points, leading to low settlement payouts
    and consistent losses.
    """

    # Focus on traditionally slow teams
    FOCUS_DRIVERS = ["SAR", "BOT", "ZHO", "MAG", "ALB"]

    def __init__(self, user_id: int):
        super().__init__(user_id, "backmarker_fan")

    def get_trades(
        self,
        race_num: int,
        race_results: List[Tuple[str, int]],
        current_positions: Dict[str, Decimal],
        wallet_balance: Decimal,
    ) -> List[TradeAction]:
        trades = []

        # Buy backmarker drivers regardless of performance
        for driver in self.FOCUS_DRIVERS:
            # Check if driver is in the race
            in_race = any(code == driver for code, _ in race_results)
            if in_race and wallet_balance >= Decimal('1.5'):
                trades.append(TradeAction(
                    driver_code=driver,
                    action="buy",
                    quantity=Decimal('2')
                ))
                wallet_balance -= Decimal('3')

        return trades


class BadTimingStrategy(TradingStrategy):
    """Strategy: Buy high, sell low.

    Buys drivers who finished poorly (price might drop more)
    and sells winners before settlement (missing payout).
    """

    def __init__(self, user_id: int):
        super().__init__(user_id, "bad_timing")

    def get_trades(
        self,
        race_num: int,
        race_results: List[Tuple[str, int]],
        current_positions: Dict[str, Decimal],
        wallet_balance: Decimal,
    ) -> List[TradeAction]:
        trades = []

        # Buy drivers who finished poorly (likely to continue losing)
        losers = [(code, pos) for code, pos in race_results if 15 <= pos <= 20 or pos == 0]

        for driver_code, _ in losers[:2]:
            if wallet_balance >= Decimal('2'):
                trades.append(TradeAction(
                    driver_code=driver_code,
                    action="buy",
                    quantity=Decimal('2.5')
                ))
                wallet_balance -= Decimal('3')

        # Sell any profitable positions before they settle (bad move!)
        for driver, shares in current_positions.items():
            if shares > Decimal('1'):
                # Sell 70% before settlement, missing the payout
                sell_qty = shares * Decimal('0.7')
                trades.append(TradeAction(
                    driver_code=driver,
                    action="sell",
                    quantity=sell_qty
                ))

        return trades


class ChaseHypeStrategy(TradingStrategy):
    """Strategy: Buy whoever won the last race (after price already high).

    Classic buy-high behavior - buys after prices have already risen.
    """

    def __init__(self, user_id: int):
        super().__init__(user_id, "chase_hype")
        self.last_race_winners: Optional[List[str]] = None

    def get_trades(
        self,
        race_num: int,
        race_results: List[Tuple[str, int]],
        current_positions: Dict[str, Decimal],
        wallet_balance: Decimal,
    ) -> List[TradeAction]:
        trades = []

        # Buy last race's winners (price already went up)
        if race_num > 1 and self.last_race_winners:
            for driver in self.last_race_winners:
                # Buy at higher price (bad timing)
                if wallet_balance >= Decimal('3'):
                    trades.append(TradeAction(
                        driver_code=driver,
                        action="buy",
                        quantity=Decimal('2')
                    ))
                    wallet_balance -= Decimal('4')

        # Store this race's top 3 for next race
        self.last_race_winners = [
            code for code, pos in race_results if 1 <= pos <= 3
        ]

        return trades
