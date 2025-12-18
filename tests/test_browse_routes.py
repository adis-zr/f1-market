"""Tests for browse API routes."""
import pytest
from decimal import Decimal
from db import db


class TestSportsEndpoint:
    """Tests for GET /api/sports."""

    def test_get_sports(self, full_client, test_sport):
        """Test getting all sports."""
        response = full_client.get('/api/sports')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        sport = next((s for s in data if s['id'] == test_sport.id), None)
        assert sport is not None
        assert sport['code'] == 'F1'
        assert sport['name'] == 'Formula 1'


class TestLeaguesEndpoint:
    """Tests for GET /api/leagues."""

    def test_get_leagues_all(self, full_client, test_league):
        """Test getting all leagues."""
        response = full_client.get('/api/leagues')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        league = next((l for l in data if l['id'] == test_league.id), None)
        assert league is not None
        assert league['name'] == 'Formula 1'

    def test_get_leagues_filtered_by_sport(self, full_client, test_league, test_sport):
        """Test getting leagues filtered by sport."""
        response = full_client.get(f'/api/leagues?sport_id={test_sport.id}')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert all(l['sport_id'] == test_sport.id for l in data)


class TestSeasonsEndpoint:
    """Tests for GET /api/seasons."""

    def test_get_seasons_all(self, full_client, test_season):
        """Test getting all seasons."""
        response = full_client.get('/api/seasons')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        season = next((s for s in data if s['id'] == test_season.id), None)
        assert season is not None
        assert season['year'] == 2024

    def test_get_seasons_filtered_by_league(self, full_client, test_season, test_league):
        """Test getting seasons filtered by league."""
        response = full_client.get(f'/api/seasons?league_id={test_league.id}')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert all(s['league_id'] == test_league.id for s in data)


class TestEventsEndpoint:
    """Tests for GET /api/events."""

    def test_get_events_all(self, full_client, test_event):
        """Test getting all events."""
        response = full_client.get('/api/events')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        event = next((e for e in data if e['id'] == test_event.id), None)
        assert event is not None
        assert event['name'] == 'Test Grand Prix'

    def test_get_events_filtered_by_season(self, full_client, test_event, test_season):
        """Test getting events filtered by season."""
        response = full_client.get(f'/api/events?season_id={test_season.id}')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert all(e['season_id'] == test_season.id for e in data)

    def test_get_events_filtered_by_status(self, full_client, test_event):
        """Test getting events filtered by status."""
        response = full_client.get('/api/events?status=upcoming')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert all(e['status'] == 'upcoming' for e in data)

    def test_get_events_invalid_status(self, full_client):
        """Test getting events with invalid status."""
        response = full_client.get('/api/events?status=invalid_status')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Invalid status' in data['error']

    def test_get_events_with_limit(self, full_client, test_event):
        """Test getting events with limit."""
        response = full_client.get('/api/events?limit=5')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) <= 5


class TestEventMarketsEndpoint:
    """Tests for GET /api/events/<id>/markets."""

    def test_get_event_markets(self, full_client, test_event, test_market):
        """Test getting markets for an event."""
        response = full_client.get(f'/api/events/{test_event.id}/markets')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        market = next((m for m in data if m['market_id'] == test_market.id), None)
        assert market is not None
        assert 'current_price' in market
        assert 'current_supply' in market
        assert 'asset' in market

    def test_get_event_markets_empty(self, full_app, full_client, test_season, db_session):
        """Test getting markets for event with no markets."""
        from db.models import Event, EventStatus, utc_now

        # Create event with no markets
        event = Event(
            season_id=test_season.id,
            name='Empty Event',
            venue='Empty Venue',
            start_at=utc_now(),
            status=EventStatus.UPCOMING
        )
        db_session.add(event)
        db_session.commit()

        response = full_client.get(f'/api/events/{event.id}/markets')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) == 0


class TestEventResultsEndpoint:
    """Tests for GET /api/events/<id>/results."""

    def test_get_event_results(self, full_client, test_event, test_event_result):
        """Test getting results for an event."""
        response = full_client.get(f'/api/events/{test_event.id}/results')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        result = next((r for r in data if r['id'] == test_event_result.id), None)
        assert result is not None
        assert result['rank'] == 1
        assert result['primary_score'] == 25.0
        assert 'participant' in result

    def test_get_event_results_empty(self, full_client, test_event):
        """Test getting results for event with no results."""
        response = full_client.get(f'/api/events/{test_event.id}/results')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)


class TestMarketsEndpoint:
    """Tests for GET /api/markets."""

    def test_get_markets_all(self, full_client, test_market):
        """Test getting all markets."""
        response = full_client.get('/api/markets')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        market = next((m for m in data if m['market_id'] == test_market.id), None)
        assert market is not None
        assert 'current_price' in market
        assert 'bonding_curve_a' in market
        assert 'bonding_curve_b' in market

    def test_get_markets_filtered_by_event(self, full_client, test_market, test_event):
        """Test getting markets filtered by event."""
        response = full_client.get(f'/api/markets?event_id={test_event.id}')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert all(m['event_id'] == test_event.id for m in data)

    def test_get_markets_filtered_by_status(self, full_client, test_market):
        """Test getting markets filtered by status."""
        response = full_client.get('/api/markets?status=open')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert all(m['status'] == 'open' for m in data)


class TestPortfolioEndpoint:
    """Tests for GET /api/portfolio."""

    def test_get_portfolio_authenticated(self, full_app, test_user, test_market, test_wallet):
        """Test getting portfolio when authenticated with positions."""
        client = full_app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = test_user.id
            sess['email'] = test_user.email
            sess['username'] = test_user.username
            sess['role'] = test_user.role

        # Create a position within app context
        with full_app.app_context():
            from services.market_service import MarketService
            MarketService.buy_shares(test_user.id, test_market.id, Decimal('10.0'))
            db.session.commit()

        # Make request outside app_context to simulate normal request
        response = client.get('/api/portfolio')

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.get_json()}"
        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        position = data[0]
        assert 'shares' in position
        assert 'avg_entry_price' in position
        assert 'realized_pnl' in position
        assert 'current_price' in position
        assert 'unrealized_pnl' in position

    def test_get_portfolio_unauthenticated(self, full_client):
        """Test getting portfolio without authentication."""
        response = full_client.get('/api/portfolio')

        assert response.status_code == 401
        data = response.get_json()
        assert 'Authentication required' in data['error']


class TestWalletEndpoint:
    """Tests for GET /api/wallet."""

    def test_get_wallet_authenticated(self, authenticated_client, test_wallet):
        """Test getting wallet when authenticated."""
        response = authenticated_client.get('/api/wallet')

        assert response.status_code == 200
        data = response.get_json()
        assert 'available_balance' in data
        assert 'total_balance' in data
        assert 'locked_balance' in data
        assert data['total_balance'] == 1000.0

    def test_get_wallet_unauthenticated(self, full_client):
        """Test getting wallet without authentication."""
        response = full_client.get('/api/wallet')

        assert response.status_code == 401
        data = response.get_json()
        assert 'Authentication required' in data['error']


class TestLedgerEndpoint:
    """Tests for GET /api/wallet/ledger."""

    def test_get_ledger_authenticated(self, authenticated_client, test_wallet):
        """Test getting ledger when authenticated."""
        response = authenticated_client.get('/api/wallet/ledger')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        # Should have at least the deposit from test_wallet fixture
        assert len(data) >= 1
        entry = data[0]
        assert 'amount' in entry
        assert 'transaction_type' in entry
        assert 'created_at' in entry

    def test_get_ledger_filtered_by_type(self, authenticated_client, test_wallet):
        """Test getting ledger filtered by transaction type."""
        response = authenticated_client.get('/api/wallet/ledger?type=deposit')

        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)
        assert all(e['transaction_type'] == 'deposit' for e in data)

    def test_get_ledger_invalid_type(self, authenticated_client, test_wallet):
        """Test getting ledger with invalid transaction type."""
        response = authenticated_client.get('/api/wallet/ledger?type=invalid_type')

        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid transaction type' in data['error']

    def test_get_ledger_unauthenticated(self, full_client):
        """Test getting ledger without authentication."""
        response = full_client.get('/api/wallet/ledger')

        assert response.status_code == 401
        data = response.get_json()
        assert 'Authentication required' in data['error']
