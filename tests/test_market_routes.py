"""Tests for market API routes."""
import pytest
from decimal import Decimal
from db import db, MarketStatus, Market


class TestGetMarket:
    """Tests for GET /api/markets/<id>."""

    def test_get_market_success(self, full_client, test_market):
        """Test getting market information."""
        response = full_client.get(f'/api/markets/{test_market.id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['market_id'] == test_market.id
        assert data['status'] == MarketStatus.OPEN.value
        assert 'current_price' in data
        assert 'current_supply' in data

    def test_get_market_not_found(self, full_client):
        """Test getting non-existent market."""
        response = full_client.get('/api/markets/99999')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()


class TestBuyShares:
    """Tests for POST /api/markets/<id>/buy."""

    def test_buy_shares_success(self, authenticated_client, test_market, test_wallet):
        """Test successful share purchase."""
        response = authenticated_client.post(
            f'/api/markets/{test_market.id}/buy',
            json={'quantity': 10.0}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['quantity'] == 10.0
        assert 'cost' in data

    def test_buy_shares_unauthenticated(self, full_client, test_market):
        """Test buying shares without authentication."""
        response = full_client.post(
            f'/api/markets/{test_market.id}/buy',
            json={'quantity': 10.0}
        )

        assert response.status_code == 401
        data = response.get_json()
        assert 'Authentication required' in data['error']

    def test_buy_shares_missing_quantity(self, authenticated_client, test_market, test_wallet):
        """Test buying shares without quantity."""
        response = authenticated_client.post(
            f'/api/markets/{test_market.id}/buy',
            json={}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'quantity is required' in data['error']

    def test_buy_shares_invalid_quantity_format(self, authenticated_client, test_market, test_wallet):
        """Test buying shares with invalid quantity format."""
        response = authenticated_client.post(
            f'/api/markets/{test_market.id}/buy',
            json={'quantity': 'not-a-number'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid quantity' in data['error']

    def test_buy_shares_negative_quantity(self, authenticated_client, test_market, test_wallet):
        """Test buying shares with negative quantity."""
        response = authenticated_client.post(
            f'/api/markets/{test_market.id}/buy',
            json={'quantity': -10.0}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'positive' in data['error'].lower()

    def test_buy_shares_quantity_too_large(self, authenticated_client, test_market, test_wallet):
        """Test buying shares with quantity exceeding maximum."""
        response = authenticated_client.post(
            f'/api/markets/{test_market.id}/buy',
            json={'quantity': 2000000}  # Exceeds MAX_QUANTITY of 1,000,000
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'exceeds maximum' in data['error']

    def test_buy_shares_quantity_too_small(self, authenticated_client, test_market, test_wallet):
        """Test buying shares with quantity below minimum."""
        response = authenticated_client.post(
            f'/api/markets/{test_market.id}/buy',
            json={'quantity': 0.001}  # Below MIN_QUANTITY of 0.01
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'below minimum' in data['error']

    def test_buy_shares_insufficient_balance(self, full_app, test_user, test_market):
        """Test buying shares with insufficient balance."""
        client = full_app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['email'] = test_user.email
            sess['username'] = test_user.username
            sess['role'] = test_user.role

        # Create wallet with 0 balance
        from services.wallet_service import WalletService
        with full_app.app_context():
            WalletService.get_or_create_wallet(test_user.id)

        response = client.post(
            f'/api/markets/{test_market.id}/buy',
            json={'quantity': 100.0}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'Insufficient' in data['error']

    def test_buy_shares_market_closed(self, full_app, test_user, test_market, test_wallet):
        """Test buying shares on closed market."""
        # Create a fresh client and close the market in the same context
        client = full_app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['email'] = test_user.email
            sess['username'] = test_user.username
            sess['role'] = test_user.role

        with full_app.app_context():
            market = db.session.get(Market, test_market.id)
            market.status = MarketStatus.CLOSED
            db.session.commit()

            response = client.post(
                f'/api/markets/{test_market.id}/buy',
                json={'quantity': 10.0}
            )

            assert response.status_code == 400
            data = response.get_json()
            assert 'closed' in data['error'].lower()


class TestSellShares:
    """Tests for POST /api/markets/<id>/sell."""

    def test_sell_shares_success(self, authenticated_client, test_market, test_wallet, test_position):
        """Test successful share sale."""
        response = authenticated_client.post(
            f'/api/markets/{test_market.id}/sell',
            json={'quantity': 5.0}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['quantity'] == 5.0
        assert 'payout' in data
        assert 'remaining_shares' in data

    def test_sell_shares_unauthenticated(self, full_client, test_market):
        """Test selling shares without authentication."""
        response = full_client.post(
            f'/api/markets/{test_market.id}/sell',
            json={'quantity': 5.0}
        )

        assert response.status_code == 401
        data = response.get_json()
        assert 'Authentication required' in data['error']

    def test_sell_shares_insufficient_shares(self, authenticated_client, test_market, test_wallet):
        """Test selling more shares than owned."""
        response = authenticated_client.post(
            f'/api/markets/{test_market.id}/sell',
            json={'quantity': 1000.0}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'Insufficient' in data['error']

    def test_sell_shares_market_closed(self, full_app, test_user, test_market, test_wallet):
        """Test selling shares on closed market."""
        # Create a fresh client with position
        client = full_app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['email'] = test_user.email
            sess['username'] = test_user.username
            sess['role'] = test_user.role

        with full_app.app_context():
            # First buy shares
            from services.market_service import MarketService
            MarketService.buy_shares(test_user.id, test_market.id, Decimal('10.0'))
            db.session.commit()

            # Close the market
            market = db.session.get(Market, test_market.id)
            market.status = MarketStatus.CLOSED
            db.session.commit()

            response = client.post(
                f'/api/markets/{test_market.id}/sell',
                json={'quantity': 5.0}
            )

            assert response.status_code == 400
            data = response.get_json()
            assert 'closed' in data['error'].lower()


class TestEstimateCost:
    """Tests for POST /api/markets/<id>/estimate."""

    def test_estimate_buy_cost(self, full_client, test_market):
        """Test estimating buy cost."""
        response = full_client.post(
            f'/api/markets/{test_market.id}/estimate',
            json={'quantity': 10.0, 'side': 'buy'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['side'] == 'buy'
        assert data['quantity'] == 10.0
        assert 'estimated_cost' in data
        assert 'price_per_share' in data
        assert 'current_supply' in data

    def test_estimate_sell_payout(self, full_app, full_client, test_market, test_wallet, test_position):
        """Test estimating sell payout."""
        response = full_client.post(
            f'/api/markets/{test_market.id}/estimate',
            json={'quantity': 5.0, 'side': 'sell'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['side'] == 'sell'
        assert data['quantity'] == 5.0
        assert 'estimated_payout' in data
        assert 'price_per_share' in data

    def test_estimate_invalid_side(self, full_client, test_market):
        """Test estimate with invalid side."""
        response = full_client.post(
            f'/api/markets/{test_market.id}/estimate',
            json={'quantity': 10.0, 'side': 'invalid'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'buy' in data['error'] or 'sell' in data['error']

    def test_estimate_market_not_found(self, full_client):
        """Test estimate for non-existent market."""
        response = full_client.post(
            '/api/markets/99999/estimate',
            json={'quantity': 10.0, 'side': 'buy'}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert 'not found' in data['error'].lower()


class TestPriceHistory:
    """Tests for GET /api/markets/<id>/price-history."""

    def test_get_price_history(self, full_client, test_market):
        """Test getting price history."""
        response = full_client.get(f'/api/markets/{test_market.id}/price-history')

        assert response.status_code == 200
        data = response.get_json()
        assert data['market_id'] == test_market.id
        assert 'history' in data
        assert isinstance(data['history'], list)

    def test_get_price_history_with_limit(self, full_client, test_market):
        """Test getting price history with limit."""
        response = full_client.get(
            f'/api/markets/{test_market.id}/price-history?limit=5'
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'history' in data

    def test_get_price_history_market_not_found(self, full_client):
        """Test price history for non-existent market."""
        response = full_client.get('/api/markets/99999/price-history')

        assert response.status_code == 404
        data = response.get_json()
        assert 'not found' in data['error'].lower()


class TestGetPosition:
    """Tests for GET /api/markets/<id>/positions."""

    def test_get_position_with_shares(self, authenticated_client, test_market, test_wallet, test_position):
        """Test getting position when user has shares."""
        response = authenticated_client.get(f'/api/markets/{test_market.id}/positions')

        assert response.status_code == 200
        data = response.get_json()
        assert data['shares'] == 10.0
        assert 'avg_entry_price' in data

    def test_get_position_without_shares(self, authenticated_client, test_market, test_wallet):
        """Test getting position when user has no shares."""
        response = authenticated_client.get(f'/api/markets/{test_market.id}/positions')

        assert response.status_code == 200
        data = response.get_json()
        assert data['shares'] == 0

    def test_get_position_unauthenticated(self, full_client, test_market):
        """Test getting position without authentication."""
        response = full_client.get(f'/api/markets/{test_market.id}/positions')

        assert response.status_code == 401


class TestWalletInfo:
    """Tests for GET /api/markets/<id>/wallet."""

    def test_get_wallet_info_authenticated(self, authenticated_client, test_market, test_wallet):
        """Test getting wallet info when authenticated."""
        response = authenticated_client.get(f'/api/markets/{test_market.id}/wallet')

        assert response.status_code == 200
        data = response.get_json()
        assert 'available_balance' in data
        assert 'total_balance' in data
        assert 'locked_balance' in data
        assert data['total_balance'] == 1000.0

    def test_get_wallet_info_unauthenticated(self, full_client, test_market):
        """Test getting wallet info without authentication."""
        response = full_client.get(f'/api/markets/{test_market.id}/wallet')

        assert response.status_code == 401
        data = response.get_json()
        assert 'Authentication required' in data['error']
