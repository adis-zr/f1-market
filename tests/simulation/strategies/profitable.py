"""Profitable trading strategies.

These strategies are designed to make money by buying drivers who will score well.
They have "knowledge" of race results to simulate perfect prediction.
"""
from decimal import Decimal
from typing import Dict, List, Tuple

from .base import TradingStrategy, TradeAction


class WinnerPredictorStrategy(TradingStrategy):
    """Strategy: Buy race winners and podium finishers.

    This strategy buys the top-3 finishers of each race, simulating
    a trader with perfect predictive ability.
    """

    def __init__(self, user_id: int):
        super().__init__(user_id, "winner_predictor")

    def get_trades(
        self,
        race_num: int,
        race_results: List[Tuple[str, int]],
        current_positions: Dict[str, Decimal],
        wallet_balance: Decimal,
    ) -> List[TradeAction]:
        trades = []

        # Get podium finishers (positions 1-3)
        podium = [(code, pos) for code, pos in race_results if 1 <= pos <= 3]

        for driver_code, position in podium:
            # Buy more for higher positions
            if position == 1:
                quantity = Decimal('3')
            elif position == 2:
                quantity = Decimal('2')
            else:
                quantity = Decimal('1.5')

            # Only buy if we have enough balance
            if wallet_balance >= Decimal('2'):
                trades.append(TradeAction(
                    driver_code=driver_code,
                    action="buy",
                    quantity=quantity
                ))
                # Estimate cost reduction (rough, actual is bonding curve)
                wallet_balance -= quantity * Decimal('1.5')

        return trades


class ValueHunterStrategy(TradingStrategy):
    """Strategy: Buy drivers finishing in points but outside podium.

    Targets positions 4-10 which still score points but have lower
    prices due to less hype. Good risk/reward ratio.
    """

    def __init__(self, user_id: int):
        super().__init__(user_id, "value_hunter")

    def get_trades(
        self,
        race_num: int,
        race_results: List[Tuple[str, int]],
        current_positions: Dict[str, Decimal],
        wallet_balance: Decimal,
    ) -> List[TradeAction]:
        trades = []

        # Get positions 4-10 (still score points)
        value_picks = [(code, pos) for code, pos in race_results if 4 <= pos <= 10]

        # Buy up to 4 value picks per race
        for driver_code, position in value_picks[:4]:
            quantity = Decimal('2')

            if wallet_balance >= Decimal('1.5'):
                trades.append(TradeAction(
                    driver_code=driver_code,
                    action="buy",
                    quantity=quantity
                ))
                wallet_balance -= quantity * Decimal('1')

        return trades


class MomentumTraderStrategy(TradingStrategy):
    """Strategy: Accumulate shares in consistent top performers.

    Focuses on drivers who consistently finish in top positions
    (VER, NOR, LEC) and holds through the season.
    """

    FOCUS_DRIVERS = ["VER", "NOR", "LEC", "PIA", "SAI"]

    def __init__(self, user_id: int):
        super().__init__(user_id, "momentum_trader")

    def get_trades(
        self,
        race_num: int,
        race_results: List[Tuple[str, int]],
        current_positions: Dict[str, Decimal],
        wallet_balance: Decimal,
    ) -> List[TradeAction]:
        trades = []

        # Find how our focus drivers performed
        for driver_code, position in race_results:
            if driver_code in self.FOCUS_DRIVERS and 1 <= position <= 5:
                # Buy more if they did well
                quantity = Decimal('1.5')

                if wallet_balance >= Decimal('2'):
                    trades.append(TradeAction(
                        driver_code=driver_code,
                        action="buy",
                        quantity=quantity
                    ))
                    wallet_balance -= quantity * Decimal('1.5')

        return trades
