"""Tests for market service."""
import pytest
from decimal import Decimal
from db import db
from services.market_service import (
    MarketService, MarketClosedError, InsufficientSharesError
)
from services.wallet_service import WalletService, InsufficientBalanceError
from db import MarketStatus, Market


class TestMarketService:
    """Tests for MarketService."""
    
    def test_buy_shares_success(self, app, test_user, test_market, test_wallet):
        """Test successful share purchase."""
        with app.app_context():
            quantity = Decimal('10.0')
            result = MarketService.buy_shares(test_user.id, test_market.id, quantity)
            
            assert result['success'] is True
            assert result['quantity'] == float(quantity)
            assert result['cost'] > 0
            assert result['market_id'] == test_market.id
    
    def test_buy_shares_insufficient_balance(self, app, test_user, test_market):
        """Test buy shares with insufficient balance."""
        with app.app_context():
            # Create wallet with no balance
            WalletService.get_or_create_wallet(test_user.id)
            
            quantity = Decimal('1000000.0')  # Very large quantity
            
            with pytest.raises(InsufficientBalanceError):
                MarketService.buy_shares(test_user.id, test_market.id, quantity)
    
    def test_buy_shares_market_closed(self, app, test_user, test_market, test_wallet):
        """Test buy shares on closed market."""
        with app.app_context():
            # Close market
            test_market.status = MarketStatus.CLOSED
            db.session.commit()
            
            quantity = Decimal('10.0')
            
            with pytest.raises(MarketClosedError):
                MarketService.buy_shares(test_user.id, test_market.id, quantity)
    
    def test_sell_shares_success(self, app, test_user, test_market, test_wallet):
        """Test successful share sale."""
        with app.app_context():
            # First buy some shares
            buy_quantity = Decimal('10.0')
            MarketService.buy_shares(test_user.id, test_market.id, buy_quantity)
            
            # Then sell some
            sell_quantity = Decimal('5.0')
            result = MarketService.sell_shares(test_user.id, test_market.id, sell_quantity)
            
            assert result['success'] is True
            assert result['quantity'] == float(sell_quantity)
            assert result['payout'] > 0
            assert result['remaining_shares'] == float(buy_quantity - sell_quantity)
    
    def test_sell_shares_insufficient_shares(self, app, test_user, test_market, test_wallet):
        """Test sell shares with insufficient shares."""
        with app.app_context():
            quantity = Decimal('100.0')
            
            with pytest.raises(InsufficientSharesError):
                MarketService.sell_shares(test_user.id, test_market.id, quantity)
    
    def test_sell_shares_market_closed(self, app, test_user, test_market, test_wallet):
        """Test sell shares on closed market."""
        with app.app_context():
            # Buy shares first
            MarketService.buy_shares(test_user.id, test_market.id, Decimal('10.0'))
            
            # Close market
            test_market.status = MarketStatus.CLOSED
            db.session.commit()
            
            with pytest.raises(MarketClosedError):
                MarketService.sell_shares(test_user.id, test_market.id, Decimal('5.0'))
    
    def test_get_market_info(self, app, test_market):
        """Test getting market information."""
        with app.app_context():
            info = MarketService.get_market_info(test_market.id)
            
            assert info is not None
            assert info['market_id'] == test_market.id
            assert info['status'] == MarketStatus.OPEN.value
            assert 'current_price' in info
            assert 'current_supply' in info
    
    def test_get_user_position(self, app, test_user, test_market, test_wallet):
        """Test getting user position."""
        with app.app_context():
            # Buy some shares
            quantity = Decimal('10.0')
            MarketService.buy_shares(test_user.id, test_market.id, quantity)
            
            # Get position
            position = MarketService.get_user_position(test_user.id, test_market.id)
            
            assert position is not None
            assert position['shares'] == float(quantity)
            assert 'avg_entry_price' in position
            assert 'realized_pnl' in position
    
    def test_position_avg_entry_price(self, app, test_user, test_market, test_wallet):
        """Test that average entry price is calculated correctly."""
        with app.app_context():
            # Buy shares in two transactions
            MarketService.buy_shares(test_user.id, test_market.id, Decimal('10.0'))
            MarketService.buy_shares(test_user.id, test_market.id, Decimal('10.0'))
            
            position = MarketService.get_user_position(test_user.id, test_market.id)
            
            assert position['shares'] == 20.0
            assert position['avg_entry_price'] > 0

