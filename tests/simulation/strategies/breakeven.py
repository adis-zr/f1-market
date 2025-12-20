"""Break-even trading strategies.

These strategies are designed to roughly break even through
random or diversified trading that wins some and loses some.
"""
import random
from decimal import Decimal
from typing import Dict, List, Tuple

from .base import TradingStrategy, TradeAction


class RandomTraderStrategy(TradingStrategy):
    """Strategy: Random buying and selling.

    Uses deterministic pseudo-random based on race number and seed
    for reproducibility in tests.
    """

    def __init__(self, user_id: int, seed: int):
        super().__init__(user_id, f"random_trader_{seed}")
        self.seed = seed

    def get_trades(
        self,
        race_num: int,
        race_results: List[Tuple[str, int]],
        current_positions: Dict[str, Decimal],
        wallet_balance: Decimal,
    ) -> List[TradeAction]:
        # Deterministic random for reproducibility
        rng = random.Random(self.seed + race_num * 100)

        trades = []
        all_drivers = [code for code, pos in race_results if pos > 0]

        # Randomly buy 1-3 drivers
        num_buys = rng.randint(1, 3)
        if len(all_drivers) >= num_buys:
            buy_drivers = rng.sample(all_drivers, num_buys)

            for driver in buy_drivers:
                quantity = Decimal(str(round(rng.uniform(0.5, 2.0), 2)))
                if wallet_balance >= Decimal('1'):
                    trades.append(TradeAction(
                        driver_code=driver,
                        action="buy",
                        quantity=quantity
                    ))
                    wallet_balance -= quantity * Decimal('1')

        # Randomly sell from existing positions (30% chance per position)
        for driver, shares in current_positions.items():
            if shares > Decimal('0.5') and rng.random() > 0.7:
                sell_qty = shares * Decimal(str(round(rng.uniform(0.3, 0.6), 2)))
                if sell_qty > Decimal('0.1'):
                    trades.append(TradeAction(
                        driver_code=driver,
                        action="sell",
                        quantity=sell_qty
                    ))

        return trades


class DiversifiedTraderStrategy(TradingStrategy):
    """Strategy: Spread small bets across many drivers.

    Buys small amounts of multiple drivers to diversify risk.
    Wins some, loses some, approximately breaks even.
    """

    def __init__(self, user_id: int, variant: int = 0):
        super().__init__(user_id, f"diversified_{variant}")
        self.variant = variant

    def get_trades(
        self,
        race_num: int,
        race_results: List[Tuple[str, int]],
        current_positions: Dict[str, Decimal],
        wallet_balance: Decimal,
    ) -> List[TradeAction]:
        trades = []

        # Get midfield drivers (positions 6-15)
        midfield = [(code, pos) for code, pos in race_results if 6 <= pos <= 15]

        # Use variant to pick different subsets
        rng = random.Random(self.variant + race_num)
        rng.shuffle(midfield)

        # Buy small amounts of 3-5 drivers
        for driver_code, _ in midfield[:4]:
            quantity = Decimal('0.75')
            if wallet_balance >= Decimal('0.5'):
                trades.append(TradeAction(
                    driver_code=driver_code,
                    action="buy",
                    quantity=quantity
                ))
                wallet_balance -= quantity * Decimal('0.75')

        return trades
