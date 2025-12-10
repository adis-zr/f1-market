"""Market service for buying and selling shares."""
from decimal import Decimal
from datetime import datetime
from typing import Dict, Optional
from db import db, Market, Position, Trade, PriceHistory, MarketStatus, TransactionType
from pricing.bonding_curve import buy_cost, sell_payout, get_current_supply, price
from services.wallet_service import WalletService, InsufficientBalanceError
from sqlalchemy.exc import IntegrityError


class MarketClosedError(Exception):
    """Raised when trying to trade on a closed market."""
    pass


class InsufficientSharesError(Exception):
    """Raised when user doesn't have enough shares to sell."""
    pass


class MarketService:
    """Service for market operations (buy/sell shares)."""
    
    @staticmethod
    def buy_shares(user_id: int, market_id: int, quantity: Decimal) -> Dict:
        """
        Buy shares in a market using bonding curve pricing.
        
        Args:
            user_id: User ID
            market_id: Market ID
            quantity: Number of shares to buy
        
        Returns:
            Dict with trade details
        
        Raises:
            MarketClosedError: If market is not open
            InsufficientBalanceError: If user doesn't have enough balance
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        # Start transaction
        try:
            # Get market
            market = Market.query.get(market_id)
            if not market:
                raise ValueError(f"Market {market_id} not found")
            
            # Check market status
            if market.status != MarketStatus.OPEN:
                raise MarketClosedError(f"Market {market_id} is not open (status: {market.status.value})")
            
            # Get current supply
            current_supply = get_current_supply(market_id)
            
            # Compute cost
            cost = buy_cost(
                current_supply,
                quantity,
                Decimal(str(market.a)),
                Decimal(str(market.b))
            )
            
            # Lock balance (uses flush, not commit - part of this transaction)
            WalletService.lock_balance(user_id, cost)
            
            # Get or create position
            position = Position.query.filter_by(
                user_id=user_id,
                market_id=market_id
            ).first()
            
            if position is None:
                # Create new position
                position = Position(
                    user_id=user_id,
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
                
                # Weighted average: (old_shares * old_avg + cost) / new_shares
                position.avg_entry_price = (old_shares * old_avg_price + cost) / new_shares
                position.shares = new_shares
            
            # Create ledger entry (debit) - deducts balance and releases lock
            WalletService.add_ledger_entry(
                user_id=user_id,
                amount=-cost,  # Negative for debit
                transaction_type=TransactionType.BUY,
                reference_type="market",
                reference_id=market_id,
                description=f"Buy {quantity} shares in market {market_id}"
            )
            
            # Create trade record
            trade = Trade(
                market_id=market_id,
                buyer_user_id=user_id,
                seller_user_id=None,  # AMM trade, no seller
                price=cost / quantity,  # Average price per share
                quantity=quantity,
                executed_at=datetime.utcnow()
            )
            db.session.add(trade)
            
            # Create price history entry
            new_supply = current_supply + quantity
            new_price = price(
                new_supply,
                Decimal(str(market.a)),
                Decimal(str(market.b))
            )
            price_history = PriceHistory(
                market_id=market_id,
                timestamp=datetime.utcnow(),
                price=new_price,
                reason=f"buy_{user_id}"
            )
            db.session.add(price_history)
            
            # Update market
            market.updated_at = datetime.utcnow()
            
            # Commit entire transaction atomically
            db.session.commit()
            
            return {
                "success": True,
                "market_id": market_id,
                "quantity": float(quantity),
                "cost": float(cost),
                "price_per_share": float(cost / quantity),
                "new_supply": float(new_supply),
                "new_price": float(new_price),
                "position_shares": float(position.shares),
                "trade_id": trade.id
            }
        
        except IntegrityError as e:
            db.session.rollback()
            raise ValueError(f"Database integrity error: {str(e)}")
        except Exception as e:
            db.session.rollback()
            raise
    
    @staticmethod
    def sell_shares(user_id: int, market_id: int, quantity: Decimal) -> Dict:
        """
        Sell shares in a market using bonding curve pricing.
        
        Args:
            user_id: User ID
            market_id: Market ID
            quantity: Number of shares to sell
        
        Returns:
            Dict with trade details
        
        Raises:
            MarketClosedError: If market is not open
            InsufficientSharesError: If user doesn't have enough shares
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        # Start transaction
        try:
            # Get market
            market = Market.query.get(market_id)
            if not market:
                raise ValueError(f"Market {market_id} not found")
            
            # Check market status
            if market.status != MarketStatus.OPEN:
                raise MarketClosedError(f"Market {market_id} is not open (status: {market.status.value})")
            
            # Get user position
            position = Position.query.filter_by(
                user_id=user_id,
                market_id=market_id
            ).first()
            
            if not position or Decimal(str(position.shares)) < quantity:
                raise InsufficientSharesError(
                    f"Insufficient shares. Available: {position.shares if position else 0}, Required: {quantity}"
                )
            
            # Get current supply
            current_supply = get_current_supply(market_id)
            
            # Compute payout
            payout = sell_payout(
                current_supply,
                quantity,
                Decimal(str(market.a)),
                Decimal(str(market.b))
            )
            
            # Update position
            old_shares = Decimal(str(position.shares))
            old_avg_price = Decimal(str(position.avg_entry_price))
            new_shares = old_shares - quantity
            
            # Calculate realized P&L for this sale
            sale_price_per_share = payout / quantity
            cost_basis = old_avg_price
            realized_pnl_for_sale = (sale_price_per_share - cost_basis) * quantity
            
            position.shares = new_shares
            position.realized_pnl = Decimal(str(position.realized_pnl)) + realized_pnl_for_sale
            position.last_marked_at = datetime.utcnow()
            
            # If all shares sold, we could delete the position, but we'll keep it for history
            # Optionally: if new_shares == 0, we could delete it
            
            # Create ledger entry (credit)
            WalletService.add_ledger_entry(
                user_id=user_id,
                amount=payout,  # Positive for credit
                transaction_type=TransactionType.SELL,
                reference_type="market",
                reference_id=market_id,
                description=f"Sell {quantity} shares in market {market_id}"
            )
            
            # Create trade record
            trade = Trade(
                market_id=market_id,
                buyer_user_id=None,  # AMM trade, no buyer
                seller_user_id=user_id,
                price=payout / quantity,  # Average price per share
                quantity=quantity,
                executed_at=datetime.utcnow()
            )
            db.session.add(trade)
            
            # Create price history entry
            new_supply = current_supply - quantity
            new_price = price(
                new_supply,
                Decimal(str(market.a)),
                Decimal(str(market.b))
            )
            price_history = PriceHistory(
                market_id=market_id,
                timestamp=datetime.utcnow(),
                price=new_price,
                reason=f"sell_{user_id}"
            )
            db.session.add(price_history)
            
            # Update market
            market.updated_at = datetime.utcnow()
            
            # Commit transaction
            db.session.commit()
            
            return {
                "success": True,
                "market_id": market_id,
                "quantity": float(quantity),
                "payout": float(payout),
                "price_per_share": float(payout / quantity),
                "realized_pnl": float(realized_pnl_for_sale),
                "new_supply": float(new_supply),
                "new_price": float(new_price),
                "remaining_shares": float(new_shares),
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
        """
        Get market information including current price and supply.
        
        Args:
            market_id: Market ID
        
        Returns:
            Dict with market info or None if not found
        """
        market = Market.query.get(market_id)
        if not market:
            return None
        
        current_supply = get_current_supply(market_id)
        current_price = price(
            current_supply,
            Decimal(str(market.a)),
            Decimal(str(market.b))
        )
        
        return {
            "market_id": market.id,
            "event_id": market.event_id,
            "asset_id": market.asset_id,
            "status": market.status.value,
            "current_supply": float(current_supply),
            "current_price": float(current_price),
            "bonding_curve_a": float(market.a),
            "bonding_curve_b": float(market.b),
            "market_type": market.market_type,
            "created_at": market.created_at.isoformat() if market.created_at else None,
            "updated_at": market.updated_at.isoformat() if market.updated_at else None
        }
    
    @staticmethod
    def get_user_position(user_id: int, market_id: int) -> Optional[Dict]:
        """
        Get user's position in a market.
        
        Args:
            user_id: User ID
            market_id: Market ID
        
        Returns:
            Dict with position info or None if no position
        """
        position = Position.query.filter_by(
            user_id=user_id,
            market_id=market_id
        ).first()
        
        if not position:
            return None
        
        # Get current market price for unrealized P&L
        market = Market.query.get(market_id)
        if market:
            current_supply = get_current_supply(market_id)
            current_price = price(
                current_supply,
                Decimal(str(market.a)),
                Decimal(str(market.b))
            )
            shares = Decimal(str(position.shares))
            avg_entry = Decimal(str(position.avg_entry_price))
            unrealized_pnl = (current_price - avg_entry) * shares
        else:
            current_price = None
            unrealized_pnl = None
        
        return {
            "position_id": position.id,
            "market_id": market_id,
            "shares": float(position.shares),
            "avg_entry_price": float(position.avg_entry_price),
            "realized_pnl": float(position.realized_pnl),
            "current_price": float(current_price) if current_price else None,
            "unrealized_pnl": float(unrealized_pnl) if unrealized_pnl else None,
            "total_pnl": float(position.realized_pnl + unrealized_pnl) if unrealized_pnl else float(position.realized_pnl),
            "last_marked_at": position.last_marked_at.isoformat() if position.last_marked_at else None
        }

