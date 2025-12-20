"""State snapshot utilities for simulation tests.

Captures complete system state at any point for comparison and debugging.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Optional


@dataclass
class UserSnapshot:
    """Snapshot of a user's state."""
    user_id: int
    wallet_balance: Decimal
    wallet_locked: Decimal
    positions: Dict[int, Dict]  # market_id -> {shares, avg_entry_price, realized_pnl}
    ledger_count: int
    total_invested: Decimal = Decimal('0')
    total_realized_pnl: Decimal = Decimal('0')

    def __post_init__(self):
        """Calculate derived values."""
        self.total_invested = sum(
            Decimal(str(p.get('shares', 0))) * Decimal(str(p.get('avg_entry_price', 0)))
            for p in self.positions.values()
        )
        self.total_realized_pnl = sum(
            Decimal(str(p.get('realized_pnl', 0)))
            for p in self.positions.values()
        )


@dataclass
class MarketSnapshot:
    """Snapshot of a market's state."""
    market_id: int
    driver_code: str
    status: str
    current_supply: Decimal
    current_price: Decimal
    trade_count: int


@dataclass
class SystemSnapshot:
    """Complete system state at a point in time."""
    snapshot_id: str
    users: Dict[int, UserSnapshot] = field(default_factory=dict)
    markets: Dict[int, MarketSnapshot] = field(default_factory=dict)
    # Lookup by driver code for convenience
    markets_by_driver: Dict[str, MarketSnapshot] = field(default_factory=dict)

    @property
    def total_wallet_balance(self) -> Decimal:
        """Sum of all user wallet balances."""
        return sum(u.wallet_balance for u in self.users.values())

    @property
    def total_supply(self) -> Decimal:
        """Sum of all market supplies."""
        return sum(m.current_supply for m in self.markets.values())

    def get_user_position_shares(self, user_id: int, market_id: int) -> Decimal:
        """Get shares held by user in market."""
        user = self.users.get(user_id)
        if not user:
            return Decimal('0')
        pos = user.positions.get(market_id, {})
        return Decimal(str(pos.get('shares', 0)))

    def diff(self, other: 'SystemSnapshot') -> Dict:
        """Compare two snapshots and return differences.

        Args:
            other: The other snapshot to compare against

        Returns:
            Dict with wallet_changes, position_changes, market_changes
        """
        changes = {
            'wallet_changes': {},
            'position_changes': {},
            'market_changes': {},
        }

        # Compare user wallets
        for user_id, user in self.users.items():
            if user_id in other.users:
                old_balance = other.users[user_id].wallet_balance
                new_balance = user.wallet_balance
                if old_balance != new_balance:
                    changes['wallet_changes'][user_id] = {
                        'old': old_balance,
                        'new': new_balance,
                        'diff': new_balance - old_balance
                    }

        # Compare positions
        for user_id, user in self.users.items():
            if user_id not in other.users:
                continue
            for market_id, pos in user.positions.items():
                old_pos = other.users[user_id].positions.get(market_id, {})
                old_shares = Decimal(str(old_pos.get('shares', 0)))
                new_shares = Decimal(str(pos.get('shares', 0)))
                if old_shares != new_shares:
                    key = (user_id, market_id)
                    changes['position_changes'][key] = {
                        'old_shares': old_shares,
                        'new_shares': new_shares,
                        'diff': new_shares - old_shares
                    }

        # Compare markets
        for market_id, market in self.markets.items():
            if market_id in other.markets:
                old_supply = other.markets[market_id].current_supply
                new_supply = market.current_supply
                if old_supply != new_supply:
                    changes['market_changes'][market_id] = {
                        'old_supply': old_supply,
                        'new_supply': new_supply,
                        'diff': new_supply - old_supply
                    }

        return changes


class SnapshotCapture:
    """Utility to capture system state snapshots."""

    def __init__(self, app):
        """Initialize with Flask app for context."""
        self.app = app

    def capture(self, snapshot_id: str) -> SystemSnapshot:
        """Capture current system state.

        Args:
            snapshot_id: Identifier for this snapshot

        Returns:
            SystemSnapshot with current state
        """
        from db import db
        from db.models import User, Wallet, Position, Market, Trade, LedgerEntry
        from pricing.bonding_curve import get_current_supply, price

        snapshot = SystemSnapshot(snapshot_id=snapshot_id)

        # Capture user states
        for user in User.query.all():
            wallet = Wallet.query.filter_by(user_id=user.id).first()

            positions_data = {}
            for pos in Position.query.filter_by(user_id=user.id).all():
                positions_data[pos.market_id] = {
                    'shares': Decimal(str(pos.shares)),
                    'avg_entry_price': Decimal(str(pos.avg_entry_price)),
                    'realized_pnl': Decimal(str(pos.realized_pnl))
                }

            ledger_count = LedgerEntry.query.filter_by(user_id=user.id).count()

            snapshot.users[user.id] = UserSnapshot(
                user_id=user.id,
                wallet_balance=Decimal(str(wallet.balance)) if wallet else Decimal('0'),
                wallet_locked=Decimal(str(wallet.locked_balance)) if wallet else Decimal('0'),
                positions=positions_data,
                ledger_count=ledger_count
            )

        # Capture market states
        for market in Market.query.all():
            supply = get_current_supply(market.id)
            current_price = price(
                supply,
                Decimal(str(market.a)),
                Decimal(str(market.b))
            )
            trade_count = Trade.query.filter_by(market_id=market.id).count()

            # Get driver code from asset
            driver_code = ""
            if market.asset:
                driver_code = market.asset.symbol or ""

            market_snap = MarketSnapshot(
                market_id=market.id,
                driver_code=driver_code,
                status=market.status.value,
                current_supply=supply,
                current_price=current_price,
                trade_count=trade_count
            )
            snapshot.markets[market.id] = market_snap
            if driver_code:
                snapshot.markets_by_driver[driver_code] = market_snap

        return snapshot
