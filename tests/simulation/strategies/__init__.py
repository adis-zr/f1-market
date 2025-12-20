"""Trading strategies for simulation."""
from .base import TradingStrategy, TradeAction
from .profitable import WinnerPredictorStrategy, ValueHunterStrategy, MomentumTraderStrategy
from .breakeven import RandomTraderStrategy, DiversifiedTraderStrategy
from .losing import BackmarkerFanStrategy, BadTimingStrategy, ChaseHypeStrategy

__all__ = [
    'TradingStrategy',
    'TradeAction',
    'WinnerPredictorStrategy',
    'ValueHunterStrategy',
    'MomentumTraderStrategy',
    'RandomTraderStrategy',
    'DiversifiedTraderStrategy',
    'BackmarkerFanStrategy',
    'BadTimingStrategy',
    'ChaseHypeStrategy',
]
