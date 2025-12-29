"""Tests for replay API routes."""
import pytest
from decimal import Decimal
from db import db
from db.replay_models import (
    ReplaySession, ReplaySessionStatus, ReplayWallet, ReplayMarket,
    ReplayPosition, ReplayTrade, ReplayLedgerEntry, ReplayDifficulty
)


@pytest.fixture
def replay_app(full_app):
    """App with replay blueprint registered."""
    from api.replay_routes import bp as replay_bp

    if 'replay' not in full_app.blueprints:
        full_app.register_blueprint(replay_bp)

    return full_app


@pytest.fixture
def replay_client(replay_app):
    """Client for replay routes."""
    return replay_app.test_client()


@pytest.fixture
def authenticated_replay_client(replay_app, test_user):
    """Authenticated client for replay routes."""
    client = replay_app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
        sess['email'] = test_user.email
        sess['username'] = test_user.username
        sess['role'] = test_user.role
    return client


@pytest.fixture
def replay_session(db_session, test_user):
    """Create a replay session for testing."""
    from services.replay_service import ReplayService
    from services.replay_ai_service import ReplayAIService

    # Ensure AI players exist
    ReplayAIService.ensure_ai_players_exist()

    state = ReplayService.start_replay(test_user.id, ReplayDifficulty.MEDIUM)
    session = ReplaySession.query.filter_by(user_id=test_user.id).first()
    return session


@pytest.fixture
def replay_session_with_race(db_session, test_user):
    """Create a replay session advanced to race 1."""
    from services.replay_service import ReplayService
    from services.replay_ai_service import ReplayAIService

    ReplayAIService.ensure_ai_players_exist()
    ReplayService.start_replay(test_user.id, ReplayDifficulty.MEDIUM)

    session = ReplaySession.query.filter_by(user_id=test_user.id).first()
    ReplayService.advance_to_next_race(session.id)

    db_session.refresh(session)
    return session


# =============================================================================
# Session Management Tests
# =============================================================================

class TestStartReplay:
    """Tests for POST /api/replay/start."""

    def test_start_replay_success(self, authenticated_replay_client, db_session):
        """Test starting a new replay session."""
        response = authenticated_replay_client.post('/api/replay/start', json={})

        assert response.status_code == 201
        data = response.get_json()
        assert 'session' in data
        assert data['session']['status'] == 'active'
        assert data['session']['current_race'] == 0
        assert data['wallet']['balance'] == 100.0

    def test_start_replay_with_difficulty(self, authenticated_replay_client, db_session):
        """Test starting with specific difficulty."""
        response = authenticated_replay_client.post(
            '/api/replay/start',
            json={'difficulty': 'hard'}
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['session']['difficulty'] == 'hard'

    def test_start_replay_invalid_difficulty(self, authenticated_replay_client, db_session):
        """Test starting with invalid difficulty."""
        response = authenticated_replay_client.post(
            '/api/replay/start',
            json={'difficulty': 'impossible'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid difficulty' in data['error']

    def test_start_replay_returns_existing(self, authenticated_replay_client, replay_session):
        """Test that starting returns existing active session."""
        response = authenticated_replay_client.post('/api/replay/start')

        assert response.status_code == 200  # Not 201, returns existing
        data = response.get_json()
        assert data['session']['session_id'] == replay_session.id

    def test_start_replay_unauthenticated(self, replay_client):
        """Test starting without authentication."""
        response = replay_client.post('/api/replay/start')

        assert response.status_code == 401
        data = response.get_json()
        assert 'Authentication required' in data['error']


class TestGetSession:
    """Tests for GET /api/replay/session."""

    def test_get_session_success(self, authenticated_replay_client, replay_session):
        """Test getting current session state."""
        response = authenticated_replay_client.get('/api/replay/session')

        assert response.status_code == 200
        data = response.get_json()
        assert data['session']['session_id'] == replay_session.id
        assert 'wallet' in data
        assert 'positions' in data
        assert 'all_races' in data

    def test_get_session_no_active(self, authenticated_replay_client):
        """Test getting session when none exists."""
        response = authenticated_replay_client.get('/api/replay/session')

        assert response.status_code == 404
        data = response.get_json()
        assert 'No active replay session' in data['error']

    def test_get_session_unauthenticated(self, replay_client):
        """Test getting session without authentication."""
        response = replay_client.get('/api/replay/session')

        assert response.status_code == 401


class TestResetReplay:
    """Tests for POST /api/replay/reset."""

    def test_reset_replay_success(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test resetting a replay session."""
        # Verify we have markets
        markets_before = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).count()
        assert markets_before > 0

        response = authenticated_replay_client.post('/api/replay/reset')

        assert response.status_code == 200
        data = response.get_json()
        assert data['session']['current_race'] == 0
        assert data['wallet']['balance'] == 100.0

        # Markets should be deleted
        markets_after = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).count()
        assert markets_after == 0

    def test_reset_replay_no_session(self, authenticated_replay_client):
        """Test resetting when no session exists."""
        response = authenticated_replay_client.post('/api/replay/reset')

        assert response.status_code == 404

    def test_reset_replay_unauthenticated(self, replay_client):
        """Test resetting without authentication."""
        response = replay_client.post('/api/replay/reset')

        assert response.status_code == 401


# =============================================================================
# Race Progression Tests
# =============================================================================

class TestAdvanceRace:
    """Tests for POST /api/replay/advance."""

    def test_advance_to_first_race(self, authenticated_replay_client, replay_session, db_session):
        """Test advancing from race 0 to race 1."""
        response = authenticated_replay_client.post('/api/replay/advance')

        assert response.status_code == 200
        data = response.get_json()
        assert data['settlement_summary'] is None  # No settlement for first advance
        assert data['new_state']['session']['current_race'] == 1
        assert len(data['new_state']['markets']) == 20  # 20 drivers

    def test_advance_with_settlement(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test advancing with race settlement."""
        response = authenticated_replay_client.post('/api/replay/advance')

        assert response.status_code == 200
        data = response.get_json()
        assert data['settlement_summary'] is not None
        assert 'race_name' in data['settlement_summary']
        assert 'results' in data['settlement_summary']
        assert data['new_state']['session']['current_race'] == 2

    def test_advance_no_session(self, authenticated_replay_client):
        """Test advancing when no session exists."""
        response = authenticated_replay_client.post('/api/replay/advance')

        assert response.status_code == 404

    def test_advance_unauthenticated(self, replay_client):
        """Test advancing without authentication."""
        response = replay_client.post('/api/replay/advance')

        assert response.status_code == 401


# =============================================================================
# Market Tests
# =============================================================================

class TestGetMarkets:
    """Tests for GET /api/replay/markets."""

    def test_get_markets_success(self, authenticated_replay_client, replay_session_with_race):
        """Test getting markets for current race."""
        response = authenticated_replay_client.get('/api/replay/markets')

        assert response.status_code == 200
        data = response.get_json()
        assert 'markets' in data
        assert len(data['markets']) == 20  # 20 drivers

    def test_get_markets_no_race(self, authenticated_replay_client, replay_session):
        """Test getting markets when no race started."""
        response = authenticated_replay_client.get('/api/replay/markets')

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['markets']) == 0

    def test_get_markets_no_session(self, authenticated_replay_client):
        """Test getting markets when no session exists."""
        response = authenticated_replay_client.get('/api/replay/markets')

        assert response.status_code == 404


class TestGetMarket:
    """Tests for GET /api/replay/markets/<id>."""

    def test_get_market_success(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test getting specific market details."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        response = authenticated_replay_client.get(f'/api/replay/markets/{market.id}')

        assert response.status_code == 200
        data = response.get_json()
        assert 'market' in data
        assert data['market']['market_id'] == market.id

    def test_get_market_not_found(self, authenticated_replay_client, replay_session_with_race):
        """Test getting non-existent market."""
        response = authenticated_replay_client.get('/api/replay/markets/99999')

        assert response.status_code == 404


class TestBuyShares:
    """Tests for POST /api/replay/markets/<id>/buy."""

    def test_buy_shares_success(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test successful share purchase."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        response = authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/buy',
            json={'quantity': 5.0}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['quantity'] == 5.0
        assert 'cost' in data
        assert 'new_balance' in data

    def test_buy_shares_missing_quantity(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test buying without quantity."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        response = authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/buy',
            json={}
        )

        assert response.status_code == 400
        assert 'quantity is required' in response.get_json()['error']

    def test_buy_shares_invalid_quantity(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test buying with invalid quantity format."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        response = authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/buy',
            json={'quantity': 'invalid'}
        )

        assert response.status_code == 400
        assert 'Invalid quantity' in response.get_json()['error']

    def test_buy_shares_negative_quantity(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test buying with negative quantity."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        response = authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/buy',
            json={'quantity': -10.0}
        )

        assert response.status_code == 400
        assert 'positive' in response.get_json()['error'].lower()

    def test_buy_shares_exceeds_balance(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test buying more than balance allows."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        response = authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/buy',
            json={'quantity': 10000.0}  # Very large quantity
        )

        assert response.status_code == 400
        # Should be insufficient balance error

    def test_buy_shares_no_session(self, authenticated_replay_client):
        """Test buying without active session."""
        response = authenticated_replay_client.post(
            '/api/replay/markets/1/buy',
            json={'quantity': 5.0}
        )

        assert response.status_code == 404


class TestSellShares:
    """Tests for POST /api/replay/markets/<id>/sell."""

    def test_sell_shares_success(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test successful share sale."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        # First buy some shares
        authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/buy',
            json={'quantity': 10.0}
        )

        # Then sell
        response = authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/sell',
            json={'quantity': 5.0}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['quantity'] == 5.0
        assert 'payout' in data

    def test_sell_shares_insufficient(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test selling more shares than owned."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        response = authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/sell',
            json={'quantity': 100.0}  # Don't own any shares
        )

        assert response.status_code == 400

    def test_sell_shares_missing_quantity(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test selling without quantity."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        response = authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/sell',
            json={}
        )

        assert response.status_code == 400


class TestEstimate:
    """Tests for POST /api/replay/markets/<id>/estimate."""

    def test_estimate_buy_success(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test buy estimate."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        response = authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/estimate',
            json={'quantity': 10.0, 'side': 'buy'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['side'] == 'buy'
        assert 'cost' in data
        assert 'price_per_share' in data

    def test_estimate_sell_success(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test sell estimate."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        # First buy some shares to create supply
        authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/buy',
            json={'quantity': 20.0}
        )

        response = authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/estimate',
            json={'quantity': 10.0, 'side': 'sell'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data['side'] == 'sell'
        assert 'payout' in data

    def test_estimate_invalid_side(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test estimate with invalid side."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        response = authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/estimate',
            json={'quantity': 10.0, 'side': 'invalid'}
        )

        assert response.status_code == 400
        assert 'side must be' in response.get_json()['error']


class TestPriceHistory:
    """Tests for GET /api/replay/markets/<id>/price-history."""

    def test_get_price_history_success(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test getting price history."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        response = authenticated_replay_client.get(f'/api/replay/markets/{market.id}/price-history')

        assert response.status_code == 200
        data = response.get_json()
        assert 'market_id' in data
        assert 'history' in data
        assert len(data['history']) >= 1  # At least initial price

    def test_get_price_history_with_limit(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test getting price history with limit."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        response = authenticated_replay_client.get(
            f'/api/replay/markets/{market.id}/price-history?limit=5'
        )

        assert response.status_code == 200


# =============================================================================
# Portfolio & Wallet Tests
# =============================================================================

class TestGetPortfolio:
    """Tests for GET /api/replay/portfolio."""

    def test_get_portfolio_success(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test getting portfolio."""
        # Buy some shares first
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()
        authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/buy',
            json={'quantity': 5.0}
        )

        response = authenticated_replay_client.get('/api/replay/portfolio')

        assert response.status_code == 200
        data = response.get_json()
        assert 'positions' in data
        assert 'total_pnl' in data
        assert len(data['positions']) >= 1

    def test_get_portfolio_empty(self, authenticated_replay_client, replay_session_with_race):
        """Test getting empty portfolio."""
        response = authenticated_replay_client.get('/api/replay/portfolio')

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['positions']) == 0

    def test_get_portfolio_no_session(self, authenticated_replay_client):
        """Test getting portfolio without session."""
        response = authenticated_replay_client.get('/api/replay/portfolio')

        assert response.status_code == 404


class TestGetWallet:
    """Tests for GET /api/replay/wallet."""

    def test_get_wallet_success(self, authenticated_replay_client, replay_session):
        """Test getting wallet balance."""
        response = authenticated_replay_client.get('/api/replay/wallet')

        assert response.status_code == 200
        data = response.get_json()
        assert 'balance' in data
        assert data['balance'] == 100.0

    def test_get_wallet_after_trade(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test wallet balance after trading."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()
        authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/buy',
            json={'quantity': 5.0}
        )

        response = authenticated_replay_client.get('/api/replay/wallet')

        assert response.status_code == 200
        data = response.get_json()
        assert data['balance'] < 100.0  # Balance should have decreased

    def test_get_wallet_no_session(self, authenticated_replay_client):
        """Test getting wallet without session."""
        response = authenticated_replay_client.get('/api/replay/wallet')

        assert response.status_code == 404


class TestGetLedger:
    """Tests for GET /api/replay/wallet/ledger."""

    def test_get_ledger_success(self, authenticated_replay_client, replay_session):
        """Test getting ledger history."""
        response = authenticated_replay_client.get('/api/replay/wallet/ledger')

        assert response.status_code == 200
        data = response.get_json()
        assert 'ledger' in data
        assert len(data['ledger']) >= 1  # At least initial deposit

    def test_get_ledger_with_trades(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test ledger after trades."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()
        authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/buy',
            json={'quantity': 5.0}
        )

        response = authenticated_replay_client.get('/api/replay/wallet/ledger')

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['ledger']) >= 2  # Deposit + buy

    def test_get_ledger_no_session(self, authenticated_replay_client):
        """Test getting ledger without session."""
        response = authenticated_replay_client.get('/api/replay/wallet/ledger')

        assert response.status_code == 404


# =============================================================================
# Race Info Tests
# =============================================================================

class TestGetRaces:
    """Tests for GET /api/replay/races."""

    def test_get_races_success(self, authenticated_replay_client, replay_session):
        """Test getting all races info."""
        response = authenticated_replay_client.get('/api/replay/races')

        assert response.status_code == 200
        data = response.get_json()
        assert 'races' in data
        assert len(data['races']) == 24  # Full season

    def test_get_races_with_progress(self, authenticated_replay_client, replay_session_with_race):
        """Test races show correct status based on progress."""
        response = authenticated_replay_client.get('/api/replay/races')

        assert response.status_code == 200
        data = response.get_json()

        # First race should be current
        race1 = next(r for r in data['races'] if r['race_number'] == 1)
        assert race1['status'] == 'current'

        # Second race should be upcoming
        race2 = next(r for r in data['races'] if r['race_number'] == 2)
        assert race2['status'] == 'upcoming'


class TestGetRaceResults:
    """Tests for GET /api/replay/races/<number>/results."""

    def test_get_race_results_success(self, authenticated_replay_client, replay_session):
        """Test getting race results."""
        response = authenticated_replay_client.get('/api/replay/races/1/results')

        assert response.status_code == 200
        data = response.get_json()
        assert data['race_number'] == 1
        assert 'results' in data
        assert len(data['results']) == 20  # All drivers

    def test_get_race_results_invalid_number(self, authenticated_replay_client, replay_session):
        """Test getting results for invalid race number."""
        response = authenticated_replay_client.get('/api/replay/races/25/results')

        assert response.status_code == 400
        assert 'Invalid race number' in response.get_json()['error']

    def test_get_race_results_zero(self, authenticated_replay_client, replay_session):
        """Test getting results for race 0."""
        response = authenticated_replay_client.get('/api/replay/races/0/results')

        assert response.status_code == 400


# =============================================================================
# Leaderboard Tests
# =============================================================================

class TestGetLeaderboard:
    """Tests for GET /api/replay/leaderboard."""

    def test_get_leaderboard_success(self, authenticated_replay_client, replay_session):
        """Test getting leaderboard."""
        response = authenticated_replay_client.get('/api/replay/leaderboard')

        assert response.status_code == 200
        data = response.get_json()
        assert 'entries' in data

    def test_get_leaderboard_with_difficulty(self, authenticated_replay_client, replay_session):
        """Test getting leaderboard filtered by difficulty."""
        response = authenticated_replay_client.get('/api/replay/leaderboard?difficulty=medium')

        assert response.status_code == 200
        data = response.get_json()
        # Should include AI players for medium difficulty
        assert 'entries' in data

    def test_get_leaderboard_invalid_difficulty(self, authenticated_replay_client, replay_session):
        """Test getting leaderboard with invalid difficulty."""
        response = authenticated_replay_client.get('/api/replay/leaderboard?difficulty=extreme')

        assert response.status_code == 400
        assert 'Invalid difficulty' in response.get_json()['error']

    def test_get_leaderboard_with_limit(self, authenticated_replay_client, replay_session):
        """Test getting leaderboard with limit."""
        response = authenticated_replay_client.get('/api/replay/leaderboard?limit=10')

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['entries']) <= 10


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_quantity_too_large(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test buying with quantity exceeding max."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        response = authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/buy',
            json={'quantity': 2000000}  # Exceeds MAX_QUANTITY
        )

        assert response.status_code == 400
        assert 'exceeds maximum' in response.get_json()['error']

    def test_quantity_too_small(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test buying with quantity below min."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        response = authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/buy',
            json={'quantity': 0.001}  # Below MIN_QUANTITY
        )

        assert response.status_code == 400
        assert 'below minimum' in response.get_json()['error']

    def test_quantity_too_many_decimals(self, authenticated_replay_client, replay_session_with_race, db_session):
        """Test buying with too many decimal places."""
        market = ReplayMarket.query.filter_by(session_id=replay_session_with_race.id).first()

        response = authenticated_replay_client.post(
            f'/api/replay/markets/{market.id}/buy',
            json={'quantity': 1.123456789012}  # Too many decimals
        )

        assert response.status_code == 400
        assert 'decimal places' in response.get_json()['error']
