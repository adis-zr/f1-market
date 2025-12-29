"""Tests for ReplayMarketService - market trading operations."""
import pytest
from decimal import Decimal
from db import db, MarketStatus
from db.replay_models import (
    ReplaySession, ReplaySessionStatus, ReplayWallet, ReplayMarket,
    ReplayPosition, ReplayTrade, ReplayLedgerEntry, ReplayDifficulty,
    ReplayPriceHistory, ReplayDriverPosition
)
from services.replay_service import (
    ReplayService, ReplaySessionNotFoundError, ReplayMarketClosedError,
    ReplayInsufficientBalanceError, ReplayInsufficientSharesError, INITIAL_BALANCE
)
from services.replay_market_service import ReplayMarketService
from services.replay_ai_service import ReplayAIService


@pytest.fixture
def setup_ai_players(db_session):
    """Ensure AI players exist for tests."""
    ReplayAIService.ensure_ai_players_exist()


@pytest.fixture
def active_session(db_session, test_user, setup_ai_players):
    """Create an active replay session at race 1."""
    ReplayService.start_replay(test_user.id)
    session = ReplaySession.query.filter_by(user_id=test_user.id).first()
    ReplayService.advance_to_next_race(session.id)
    db_session.refresh(session)
    return session


@pytest.fixture
def market_for_trading(active_session):
    """Get a market for trading tests."""
    return ReplayMarket.query.filter_by(
        session_id=active_session.id,
        race_number=1
    ).first()


# =============================================================================
# Buy Shares Tests
# =============================================================================

class TestBuyShares:
    """Tests for ReplayMarketService.buy_shares()."""

    def test_buy_shares_success(self, db_session, active_session, market_for_trading):
        """Test successful share purchase."""
        result = ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('10')
        )

        assert result['success'] is True
        assert result['quantity'] == 10.0
        assert result['cost'] > 0
        assert result['position_shares'] == 10.0

    def test_buy_shares_updates_wallet(self, db_session, active_session, market_for_trading):
        """Test that buying updates wallet balance."""
        wallet = ReplayWallet.query.filter_by(session_id=active_session.id).first()
        balance_before = wallet.balance

        result = ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('5')
        )

        db_session.refresh(wallet)
        assert wallet.balance < balance_before
        assert float(wallet.balance) == result['new_balance']

    def test_buy_shares_creates_position(self, db_session, active_session, market_for_trading):
        """Test that buying creates a position."""
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('5')
        )

        position = ReplayPosition.query.filter_by(
            session_id=active_session.id,
            market_id=market_for_trading.id
        ).first()

        assert position is not None
        assert position.shares == Decimal('5')

    def test_buy_shares_creates_trade_record(self, db_session, active_session, market_for_trading):
        """Test that buying creates a trade record."""
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('5')
        )

        trades = ReplayTrade.query.filter_by(
            session_id=active_session.id,
            market_id=market_for_trading.id
        ).all()

        assert len(trades) == 1
        assert trades[0].side == 'buy'
        assert trades[0].quantity == Decimal('5')

    def test_buy_shares_creates_ledger_entry(self, db_session, active_session, market_for_trading):
        """Test that buying creates a ledger entry."""
        entries_before = ReplayLedgerEntry.query.filter_by(
            session_id=active_session.id
        ).count()

        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('5')
        )

        entries_after = ReplayLedgerEntry.query.filter_by(
            session_id=active_session.id
        ).count()

        assert entries_after == entries_before + 1

    def test_buy_shares_updates_price_history(self, db_session, active_session, market_for_trading):
        """Test that buying updates price history."""
        history_before = ReplayPriceHistory.query.filter_by(
            market_id=market_for_trading.id
        ).count()

        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('5')
        )

        history_after = ReplayPriceHistory.query.filter_by(
            market_id=market_for_trading.id
        ).count()

        assert history_after == history_before + 1

    def test_buy_shares_updates_driver_position(self, db_session, active_session, market_for_trading):
        """Test that buying updates driver position for carry-forward."""
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('5')
        )

        driver_pos = ReplayDriverPosition.query.filter_by(
            session_id=active_session.id,
            driver_code=market_for_trading.driver_code
        ).first()

        assert driver_pos is not None
        assert driver_pos.shares == Decimal('5')

    def test_buy_shares_accumulates_position(self, db_session, active_session, market_for_trading):
        """Test that multiple buys accumulate shares."""
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('5')
        )
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('3')
        )

        position = ReplayPosition.query.filter_by(
            session_id=active_session.id,
            market_id=market_for_trading.id
        ).first()

        assert position.shares == Decimal('8')

    def test_buy_shares_weighted_average_price(self, db_session, active_session, market_for_trading):
        """Test that avg entry price uses weighted average."""
        # First buy
        result1 = ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('5')
        )
        first_cost = Decimal(str(result1['cost']))

        # Second buy (price should be higher due to bonding curve)
        result2 = ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('5')
        )
        second_cost = Decimal(str(result2['cost']))

        position = ReplayPosition.query.filter_by(
            session_id=active_session.id,
            market_id=market_for_trading.id
        ).first()

        expected_avg = (first_cost + second_cost) / Decimal('10')
        assert abs(float(position.avg_entry_price) - float(expected_avg)) < 0.01

    def test_buy_shares_insufficient_balance(self, db_session, active_session, market_for_trading):
        """Test buying with insufficient balance."""
        with pytest.raises(ReplayInsufficientBalanceError):
            ReplayMarketService.buy_shares(
                active_session.id,
                market_for_trading.id,
                Decimal('10000')  # More than $100 balance allows
            )

    def test_buy_shares_invalid_session(self, db_session, market_for_trading):
        """Test buying with invalid session."""
        with pytest.raises(ReplaySessionNotFoundError):
            ReplayMarketService.buy_shares(99999, market_for_trading.id, Decimal('5'))

    def test_buy_shares_closed_market(self, db_session, active_session, market_for_trading):
        """Test buying in a closed market."""
        market_for_trading.status = MarketStatus.CLOSED
        db_session.commit()

        with pytest.raises(ReplayMarketClosedError):
            ReplayMarketService.buy_shares(
                active_session.id,
                market_for_trading.id,
                Decimal('5')
            )

    def test_buy_shares_wrong_race(self, db_session, active_session, market_for_trading):
        """Test buying in a market from a different race."""
        # Advance to race 2
        ReplayService.advance_to_next_race(active_session.id)

        # Try to buy in race 1 market (which is now settled)
        with pytest.raises(ReplayMarketClosedError):
            ReplayMarketService.buy_shares(
                active_session.id,
                market_for_trading.id,  # This is race 1 market
                Decimal('5')
            )

    def test_buy_shares_zero_quantity(self, db_session, active_session, market_for_trading):
        """Test buying zero shares."""
        with pytest.raises(ValueError):
            ReplayMarketService.buy_shares(
                active_session.id,
                market_for_trading.id,
                Decimal('0')
            )

    def test_buy_shares_negative_quantity(self, db_session, active_session, market_for_trading):
        """Test buying negative shares."""
        with pytest.raises(ValueError):
            ReplayMarketService.buy_shares(
                active_session.id,
                market_for_trading.id,
                Decimal('-5')
            )


# =============================================================================
# Sell Shares Tests
# =============================================================================

class TestSellShares:
    """Tests for ReplayMarketService.sell_shares()."""

    def test_sell_shares_success(self, db_session, active_session, market_for_trading):
        """Test successful share sale."""
        # First buy shares
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('10')
        )

        # Then sell
        result = ReplayMarketService.sell_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('5')
        )

        assert result['success'] is True
        assert result['quantity'] == 5.0
        assert result['payout'] > 0
        assert result['remaining_shares'] == 5.0

    def test_sell_shares_updates_wallet(self, db_session, active_session, market_for_trading):
        """Test that selling updates wallet balance."""
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('10')
        )

        wallet = ReplayWallet.query.filter_by(session_id=active_session.id).first()
        balance_before = wallet.balance

        ReplayMarketService.sell_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('5')
        )

        db_session.refresh(wallet)
        assert wallet.balance > balance_before

    def test_sell_shares_updates_position(self, db_session, active_session, market_for_trading):
        """Test that selling updates position."""
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('10')
        )
        ReplayMarketService.sell_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('3')
        )

        position = ReplayPosition.query.filter_by(
            session_id=active_session.id,
            market_id=market_for_trading.id
        ).first()

        assert position.shares == Decimal('7')

    def test_sell_shares_calculates_realized_pnl(self, db_session, active_session, market_for_trading):
        """Test that selling calculates realized P&L."""
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('10')
        )
        result = ReplayMarketService.sell_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('5')
        )

        assert 'realized_pnl' in result
        position = ReplayPosition.query.filter_by(
            session_id=active_session.id,
            market_id=market_for_trading.id
        ).first()
        assert position.realized_pnl != 0

    def test_sell_all_shares(self, db_session, active_session, market_for_trading):
        """Test selling all shares."""
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('10')
        )
        result = ReplayMarketService.sell_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('10')
        )

        assert result['remaining_shares'] == 0

    def test_sell_shares_insufficient_shares(self, db_session, active_session, market_for_trading):
        """Test selling more shares than owned."""
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('5')
        )

        with pytest.raises(ReplayInsufficientSharesError):
            ReplayMarketService.sell_shares(
                active_session.id,
                market_for_trading.id,
                Decimal('10')
            )

    def test_sell_shares_no_position(self, db_session, active_session, market_for_trading):
        """Test selling without owning shares."""
        with pytest.raises(ReplayInsufficientSharesError):
            ReplayMarketService.sell_shares(
                active_session.id,
                market_for_trading.id,
                Decimal('5')
            )

    def test_sell_settled_market(self, db_session, active_session, market_for_trading):
        """Test selling in a settled market (for payout)."""
        # Buy shares
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('10')
        )

        # Advance to settle market
        ReplayService.advance_to_next_race(active_session.id)

        # Verify market is settled
        db_session.refresh(market_for_trading)
        assert market_for_trading.status == MarketStatus.SETTLED

        # Sell at settlement price
        result = ReplayMarketService.sell_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('5')
        )

        assert result['success'] is True
        assert result['is_settled_sale'] is True

    def test_sell_shares_updates_driver_position(self, db_session, active_session, market_for_trading):
        """Test that selling updates driver position for carry-forward."""
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('10')
        )
        ReplayMarketService.sell_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('3')
        )

        driver_pos = ReplayDriverPosition.query.filter_by(
            session_id=active_session.id,
            driver_code=market_for_trading.driver_code
        ).first()

        assert driver_pos.shares == Decimal('7')


# =============================================================================
# Estimate Cost Tests
# =============================================================================

class TestEstimateCost:
    """Tests for ReplayMarketService.estimate_cost()."""

    def test_estimate_buy_cost(self, db_session, active_session, market_for_trading):
        """Test estimating buy cost."""
        result = ReplayMarketService.estimate_cost(
            market_for_trading.id,
            Decimal('10'),
            'buy'
        )

        assert result['side'] == 'buy'
        assert result['quantity'] == 10.0
        assert 'cost' in result
        assert result['cost'] > 0
        assert 'price_per_share' in result
        assert 'new_price' in result

    def test_estimate_sell_payout(self, db_session, active_session, market_for_trading):
        """Test estimating sell payout."""
        # First buy to create supply
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('20')
        )

        result = ReplayMarketService.estimate_cost(
            market_for_trading.id,
            Decimal('10'),
            'sell'
        )

        assert result['side'] == 'sell'
        assert result['quantity'] == 10.0
        assert 'payout' in result
        assert result['payout'] > 0

    def test_estimate_shows_price_impact(self, db_session, active_session, market_for_trading):
        """Test that estimate shows price impact."""
        result = ReplayMarketService.estimate_cost(
            market_for_trading.id,
            Decimal('100'),
            'buy'
        )

        assert result['current_price'] < result['new_price']
        assert result['current_supply'] < result['new_supply']

    def test_estimate_invalid_side(self, db_session, market_for_trading):
        """Test estimate with invalid side."""
        with pytest.raises(ValueError):
            ReplayMarketService.estimate_cost(
                market_for_trading.id,
                Decimal('10'),
                'invalid'
            )

    def test_estimate_zero_quantity(self, db_session, market_for_trading):
        """Test estimate with zero quantity."""
        with pytest.raises(ValueError):
            ReplayMarketService.estimate_cost(
                market_for_trading.id,
                Decimal('0'),
                'buy'
            )

    def test_estimate_market_not_found(self, db_session):
        """Test estimate for non-existent market."""
        with pytest.raises(ValueError):
            ReplayMarketService.estimate_cost(99999, Decimal('10'), 'buy')

    def test_estimate_sell_exceeds_supply(self, db_session, market_for_trading):
        """Test estimate sell with quantity exceeding supply."""
        with pytest.raises(ValueError):
            ReplayMarketService.estimate_cost(
                market_for_trading.id,
                Decimal('1000'),  # More than supply
                'sell'
            )


# =============================================================================
# Get Market Info Tests
# =============================================================================

class TestGetMarketInfo:
    """Tests for ReplayMarketService.get_market_info()."""

    def test_get_market_info_success(self, db_session, market_for_trading):
        """Test getting market info."""
        result = ReplayMarketService.get_market_info(market_for_trading.id)

        assert result is not None
        assert result['market_id'] == market_for_trading.id
        assert result['driver_code'] == market_for_trading.driver_code
        assert result['driver_name'] == market_for_trading.driver_name
        assert 'current_price' in result
        assert 'current_supply' in result

    def test_get_market_info_not_found(self, db_session):
        """Test getting info for non-existent market."""
        result = ReplayMarketService.get_market_info(99999)

        assert result is None

    def test_get_market_info_includes_bonding_curve(self, db_session, market_for_trading):
        """Test that market info includes bonding curve params."""
        result = ReplayMarketService.get_market_info(market_for_trading.id)

        assert 'bonding_curve_a' in result
        assert 'bonding_curve_b' in result
        assert result['bonding_curve_a'] > 0


# =============================================================================
# Get Position Tests
# =============================================================================

class TestGetPosition:
    """Tests for ReplayMarketService.get_position()."""

    def test_get_position_success(self, db_session, active_session, market_for_trading):
        """Test getting position."""
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('10')
        )

        result = ReplayMarketService.get_position(
            active_session.id,
            market_for_trading.id
        )

        assert result is not None
        assert result['shares'] == 10.0
        assert 'avg_entry_price' in result
        assert 'unrealized_pnl' in result

    def test_get_position_not_found(self, db_session, active_session, market_for_trading):
        """Test getting position that doesn't exist."""
        result = ReplayMarketService.get_position(
            active_session.id,
            market_for_trading.id
        )

        assert result is None

    def test_get_position_calculates_pnl(self, db_session, active_session, market_for_trading):
        """Test that position includes P&L calculation."""
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('10')
        )

        result = ReplayMarketService.get_position(
            active_session.id,
            market_for_trading.id
        )

        assert 'unrealized_pnl' in result
        assert 'realized_pnl' in result
        assert 'total_pnl' in result


# =============================================================================
# Get Price History Tests
# =============================================================================

class TestGetPriceHistory:
    """Tests for ReplayMarketService.get_price_history()."""

    def test_get_price_history_success(self, db_session, market_for_trading):
        """Test getting price history."""
        result = ReplayMarketService.get_price_history(market_for_trading.id)

        assert isinstance(result, list)
        assert len(result) >= 1  # At least initial price

    def test_get_price_history_after_trades(self, db_session, active_session, market_for_trading):
        """Test price history after trades."""
        history_before = len(ReplayMarketService.get_price_history(market_for_trading.id))

        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('5')
        )
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('3')
        )

        history = ReplayMarketService.get_price_history(market_for_trading.id)

        assert len(history) == history_before + 2

    def test_get_price_history_respects_limit(self, db_session, active_session, market_for_trading):
        """Test price history limit."""
        # Create multiple trades
        for _ in range(5):
            ReplayMarketService.buy_shares(
                active_session.id,
                market_for_trading.id,
                Decimal('1')
            )

        result = ReplayMarketService.get_price_history(market_for_trading.id, limit=3)

        assert len(result) <= 3

    def test_get_price_history_format(self, db_session, active_session, market_for_trading):
        """Test price history entry format."""
        ReplayMarketService.buy_shares(
            active_session.id,
            market_for_trading.id,
            Decimal('5')
        )

        history = ReplayMarketService.get_price_history(market_for_trading.id)

        for entry in history:
            assert 'timestamp' in entry
            assert 'price' in entry
            assert 'supply' in entry
            assert 'reason' in entry
