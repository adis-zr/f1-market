"""Replay market service for buying and selling shares in replay mode."""
from decimal import Decimal
from typing import Dict, Optional
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from db import db, utc_now, MarketStatus, TransactionType
from db.replay_models import (
    ReplaySession, ReplaySessionStatus, ReplayWallet, ReplayMarket,
    ReplayPosition, ReplayTrade, ReplayLedgerEntry, ReplayPriceHistory
)
from pricing.bonding_curve import price, buy_cost, sell_payout
from services.replay_service import (
    ReplaySessionNotFoundError, ReplayMarketClosedError,
    ReplayInsufficientBalanceError, ReplayInsufficientSharesError
)


class ReplayMarketService:
    """Service for market operations within replay context."""

    @staticmethod
    def buy_shares(session_id: int, market_id: int, quantity: Decimal) -> Dict:
        """Buy shares in a replay market.

        Args:
            session_id: Replay session ID
            market_id: Replay market ID
            quantity: Number of shares to buy

        Returns:
            Dict with trade details

        Raises:
            ReplaySessionNotFoundError: If session not found
            ReplayMarketClosedError: If market is not open
            ReplayInsufficientBalanceError: If insufficient balance
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        try:
            # Validate session
            session = ReplaySession.query.filter_by(id=session_id).first()
            if not session:
                raise ReplaySessionNotFoundError(f"Session {session_id} not found")
            if session.status != ReplaySessionStatus.ACTIVE:
                raise ValueError(f"Session is not active (status: {session.status.value})")

            # Get market with lock
            market = ReplayMarket.query.filter_by(id=market_id).with_for_update().first()
            if not market:
                raise ValueError(f"Market {market_id} not found")
            if market.session_id != session_id:
                raise ValueError(f"Market {market_id} does not belong to session {session_id}")
            if market.status != MarketStatus.OPEN:
                raise ReplayMarketClosedError(f"Market {market_id} is not open")
            if market.race_number != session.current_race:
                raise ReplayMarketClosedError(f"Market is for race {market.race_number}, current race is {session.current_race}")

            # Get wallet with lock
            wallet = ReplayWallet.query.filter_by(session_id=session_id).with_for_update().first()
            if not wallet:
                raise ValueError(f"Wallet not found for session {session_id}")

            # Calculate cost
            current_supply = ReplayMarketService._get_market_supply(market_id)
            cost = buy_cost(
                current_supply,
                quantity,
                Decimal(str(market.a)),
                Decimal(str(market.b))
            )

            # Check balance
            available_balance = Decimal(str(wallet.balance)) - Decimal(str(wallet.locked_balance))
            if cost > available_balance:
                raise ReplayInsufficientBalanceError(
                    f"Insufficient balance. Available: {float(available_balance)}, Required: {float(cost)}"
                )

            # Deduct from wallet
            wallet.balance -= cost

            # Get or create position
            position = ReplayPosition.query.filter_by(
                session_id=session_id,
                market_id=market_id
            ).with_for_update().first()

            if position is None:
                position = ReplayPosition(
                    session_id=session_id,
                    market_id=market_id,
                    shares=quantity,
                    avg_entry_price=cost / quantity,
                    realized_pnl=Decimal('0')
                )
                db.session.add(position)
            else:
                # Update existing position (weighted average entry price)
                old_shares = Decimal(str(position.shares))
                old_avg_price = Decimal(str(position.avg_entry_price))
                new_shares = old_shares + quantity

                position.avg_entry_price = (old_shares * old_avg_price + cost) / new_shares
                position.shares = new_shares

            # Create trade record
            trade = ReplayTrade(
                session_id=session_id,
                market_id=market_id,
                side="buy",
                quantity=quantity,
                price=cost / quantity,
                cost_or_payout=cost,
                executed_at=utc_now()
            )
            db.session.add(trade)

            # Create ledger entry
            ledger = ReplayLedgerEntry(
                session_id=session_id,
                amount=-cost,
                transaction_type=TransactionType.BUY,
                reference_type="market",
                reference_id=market_id,
                description=f"Buy {float(quantity)} shares of {market.driver_code}"
            )
            db.session.add(ledger)

            # Create price history entry
            new_supply = current_supply + quantity
            new_price = price(
                new_supply,
                Decimal(str(market.a)),
                Decimal(str(market.b))
            )
            price_history = ReplayPriceHistory(
                market_id=market_id,
                timestamp=utc_now(),
                price=new_price,
                supply=new_supply,
                reason="buy"
            )
            db.session.add(price_history)

            db.session.commit()

            return {
                "success": True,
                "market_id": market_id,
                "driver_code": market.driver_code,
                "quantity": float(quantity),
                "cost": float(cost),
                "price_per_share": float(cost / quantity),
                "new_supply": float(new_supply),
                "new_price": float(new_price),
                "position_shares": float(position.shares),
                "new_balance": float(wallet.balance),
                "trade_id": trade.id
            }

        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Database integrity error: {str(e)}")
        except Exception as e:
            db.session.rollback()
            raise

    @staticmethod
    def sell_shares(session_id: int, market_id: int, quantity: Decimal) -> Dict:
        """Sell shares in a replay market.

        Args:
            session_id: Replay session ID
            market_id: Replay market ID
            quantity: Number of shares to sell

        Returns:
            Dict with trade details

        Raises:
            ReplaySessionNotFoundError: If session not found
            ReplayMarketClosedError: If market is not open
            ReplayInsufficientSharesError: If insufficient shares
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        try:
            # Validate session
            session = ReplaySession.query.filter_by(id=session_id).first()
            if not session:
                raise ReplaySessionNotFoundError(f"Session {session_id} not found")
            if session.status != ReplaySessionStatus.ACTIVE:
                raise ValueError(f"Session is not active (status: {session.status.value})")

            # Get market with lock
            market = ReplayMarket.query.filter_by(id=market_id).with_for_update().first()
            if not market:
                raise ValueError(f"Market {market_id} not found")
            if market.session_id != session_id:
                raise ValueError(f"Market {market_id} does not belong to session {session_id}")
            if market.status != MarketStatus.OPEN:
                raise ReplayMarketClosedError(f"Market {market_id} is not open")
            if market.race_number != session.current_race:
                raise ReplayMarketClosedError(f"Market is for race {market.race_number}, current race is {session.current_race}")

            # Get position with lock
            position = ReplayPosition.query.filter_by(
                session_id=session_id,
                market_id=market_id
            ).with_for_update().first()

            if not position or Decimal(str(position.shares)) < quantity:
                available = float(position.shares) if position else 0
                raise ReplayInsufficientSharesError(
                    f"Insufficient shares. Available: {available}, Required: {float(quantity)}"
                )

            # Get wallet with lock
            wallet = ReplayWallet.query.filter_by(session_id=session_id).with_for_update().first()
            if not wallet:
                raise ValueError(f"Wallet not found for session {session_id}")

            # Calculate payout
            current_supply = ReplayMarketService._get_market_supply(market_id)
            payout = sell_payout(
                current_supply,
                quantity,
                Decimal(str(market.a)),
                Decimal(str(market.b))
            )

            # Update wallet
            wallet.balance += payout

            # Update position
            old_shares = Decimal(str(position.shares))
            old_avg_price = Decimal(str(position.avg_entry_price))
            new_shares = old_shares - quantity

            # Calculate realized P&L for this sale
            sale_price_per_share = payout / quantity
            realized_pnl_for_sale = (sale_price_per_share - old_avg_price) * quantity

            position.shares = new_shares
            position.realized_pnl = Decimal(str(position.realized_pnl)) + realized_pnl_for_sale

            # Create trade record
            trade = ReplayTrade(
                session_id=session_id,
                market_id=market_id,
                side="sell",
                quantity=quantity,
                price=payout / quantity,
                cost_or_payout=payout,
                executed_at=utc_now()
            )
            db.session.add(trade)

            # Create ledger entry
            ledger = ReplayLedgerEntry(
                session_id=session_id,
                amount=payout,
                transaction_type=TransactionType.SELL,
                reference_type="market",
                reference_id=market_id,
                description=f"Sell {float(quantity)} shares of {market.driver_code}"
            )
            db.session.add(ledger)

            # Create price history entry
            new_supply = current_supply - quantity
            new_price = price(
                new_supply,
                Decimal(str(market.a)),
                Decimal(str(market.b))
            )
            price_history = ReplayPriceHistory(
                market_id=market_id,
                timestamp=utc_now(),
                price=new_price,
                supply=new_supply,
                reason="sell"
            )
            db.session.add(price_history)

            db.session.commit()

            return {
                "success": True,
                "market_id": market_id,
                "driver_code": market.driver_code,
                "quantity": float(quantity),
                "payout": float(payout),
                "price_per_share": float(payout / quantity),
                "realized_pnl": float(realized_pnl_for_sale),
                "new_supply": float(new_supply),
                "new_price": float(new_price),
                "remaining_shares": float(new_shares),
                "new_balance": float(wallet.balance),
                "trade_id": trade.id
            }

        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Database integrity error: {str(e)}")
        except Exception as e:
            db.session.rollback()
            raise

    @staticmethod
    def get_market_info(market_id: int) -> Optional[Dict]:
        """Get replay market information.

        Args:
            market_id: Replay market ID

        Returns:
            Dict with market info or None if not found
        """
        market = db.session.get(ReplayMarket, market_id)
        if not market:
            return None

        current_supply = ReplayMarketService._get_market_supply(market_id)
        current_price = price(
            current_supply,
            Decimal(str(market.a)),
            Decimal(str(market.b))
        )

        return {
            "market_id": market.id,
            "session_id": market.session_id,
            "race_number": market.race_number,
            "driver_code": market.driver_code,
            "driver_name": market.driver_name,
            "team_name": market.team_name,
            "status": market.status.value,
            "current_supply": float(current_supply),
            "current_price": float(current_price),
            "bonding_curve_a": float(market.a),
            "bonding_curve_b": float(market.b),
            "settlement_price": float(market.settlement_price) if market.settlement_price else None,
            "payout_per_share": float(market.payout_per_share) if market.payout_per_share else None,
            "created_at": market.created_at.isoformat() if market.created_at else None
        }

    @staticmethod
    def estimate_cost(market_id: int, quantity: Decimal, side: str) -> Dict:
        """Estimate buy cost or sell payout for a replay market.

        Args:
            market_id: Replay market ID
            quantity: Number of shares
            side: "buy" or "sell"

        Returns:
            Dict with estimate
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        market = db.session.get(ReplayMarket, market_id)
        if not market:
            raise ValueError(f"Market {market_id} not found")

        current_supply = ReplayMarketService._get_market_supply(market_id)
        a = Decimal(str(market.a))
        b = Decimal(str(market.b))

        if side == "buy":
            cost = buy_cost(current_supply, quantity, a, b)
            new_supply = current_supply + quantity
            new_price = price(new_supply, a, b)
            return {
                "side": "buy",
                "quantity": float(quantity),
                "cost": float(cost),
                "price_per_share": float(cost / quantity),
                "current_supply": float(current_supply),
                "new_supply": float(new_supply),
                "current_price": float(price(current_supply, a, b)),
                "new_price": float(new_price)
            }
        elif side == "sell":
            if quantity > current_supply:
                raise ValueError(f"Cannot sell more than current supply ({float(current_supply)})")
            payout = sell_payout(current_supply, quantity, a, b)
            new_supply = current_supply - quantity
            new_price = price(new_supply, a, b)
            return {
                "side": "sell",
                "quantity": float(quantity),
                "payout": float(payout),
                "price_per_share": float(payout / quantity),
                "current_supply": float(current_supply),
                "new_supply": float(new_supply),
                "current_price": float(price(current_supply, a, b)),
                "new_price": float(new_price)
            }
        else:
            raise ValueError(f"Invalid side: {side}. Must be 'buy' or 'sell'")

    @staticmethod
    def get_position(session_id: int, market_id: int) -> Optional[Dict]:
        """Get user's position in a replay market.

        Args:
            session_id: Replay session ID
            market_id: Replay market ID

        Returns:
            Dict with position info or None
        """
        position = ReplayPosition.query.filter_by(
            session_id=session_id,
            market_id=market_id
        ).first()

        if not position:
            return None

        market = db.session.get(ReplayMarket, market_id)
        if not market:
            return None

        current_supply = ReplayMarketService._get_market_supply(market_id)
        current_price = price(
            current_supply,
            Decimal(str(market.a)),
            Decimal(str(market.b))
        )

        shares = Decimal(str(position.shares))
        avg_entry = Decimal(str(position.avg_entry_price))
        unrealized_pnl = (current_price - avg_entry) * shares if shares > 0 else Decimal('0')

        return {
            "position_id": position.id,
            "market_id": market_id,
            "driver_code": market.driver_code,
            "driver_name": market.driver_name,
            "shares": float(position.shares),
            "avg_entry_price": float(position.avg_entry_price),
            "current_price": float(current_price),
            "unrealized_pnl": float(unrealized_pnl),
            "realized_pnl": float(position.realized_pnl),
            "total_pnl": float(Decimal(str(position.realized_pnl)) + unrealized_pnl)
        }

    @staticmethod
    def get_price_history(market_id: int, limit: int = 100) -> list:
        """Get price history for a replay market.

        Args:
            market_id: Replay market ID
            limit: Maximum entries to return

        Returns:
            List of price history entries
        """
        entries = ReplayPriceHistory.query.filter_by(
            market_id=market_id
        ).order_by(
            ReplayPriceHistory.timestamp.asc()
        ).limit(limit).all()

        return [
            {
                "timestamp": e.timestamp.isoformat(),
                "price": float(e.price),
                "supply": float(e.supply),
                "reason": e.reason
            }
            for e in entries
        ]

    @staticmethod
    def _get_market_supply(market_id: int) -> Decimal:
        """Get current supply for a replay market.

        Args:
            market_id: ReplayMarket ID

        Returns:
            Current supply as Decimal
        """
        result = db.session.query(func.sum(ReplayPosition.shares)).filter(
            ReplayPosition.market_id == market_id
        ).scalar()

        if result is None:
            return Decimal('0')

        return Decimal(str(result))
