"""Tests for settlement API routes."""
import pytest
from decimal import Decimal
from db import db, EventStatus


class TestSettleEvent:
    """Tests for POST /api/events/<id>/settle."""

    def test_settle_event_as_admin(self, full_app, admin_client, test_event, test_market, test_event_result, test_wallet, test_user):
        """Test settling an event as admin."""
        # First buy some shares so there's something to settle
        from services.market_service import MarketService
        with full_app.app_context():
            MarketService.buy_shares(test_user.id, test_market.id, Decimal('10.0'))
            db.session.commit()

        response = admin_client.post(
            f'/api/events/{test_event.id}/settle',
            json={'source': 'event_result'}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert 'markets_settled' in data

    def test_settle_event_as_non_admin(self, authenticated_client, test_event):
        """Test that non-admin users cannot settle events."""
        response = authenticated_client.post(
            f'/api/events/{test_event.id}/settle',
            json={'source': 'event_result'}
        )

        assert response.status_code == 403
        data = response.get_json()
        assert 'Admin access required' in data['error']

    def test_settle_event_unauthenticated(self, full_client, test_event):
        """Test that unauthenticated users cannot settle events."""
        response = full_client.post(
            f'/api/events/{test_event.id}/settle',
            json={'source': 'event_result'}
        )

        assert response.status_code == 401
        data = response.get_json()
        assert 'Authentication required' in data['error']

    def test_settle_event_not_found(self, admin_client):
        """Test settling non-existent event."""
        response = admin_client.post(
            '/api/events/99999/settle',
            json={'source': 'event_result'}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_settle_event_no_markets(self, full_app, test_admin, test_season):
        """Test settling event with no markets."""
        from db.models import Event, EventStatus, utc_now

        # Create an event with no markets
        with full_app.app_context():
            event = Event(
                season_id=test_season.id,
                name='No Markets Event',
                venue='Test Venue',
                start_at=utc_now(),
                status=EventStatus.UPCOMING
            )
            db.session.add(event)
            db.session.commit()
            event_id = event.id

        client = full_app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['email'] = test_admin.email
            sess['username'] = test_admin.username
            sess['role'] = test_admin.role

        response = client.post(
            f'/api/events/{event_id}/settle',
            json={'source': 'event_result'}
        )

        # Returns 200 with 0 markets settled when no markets exist
        assert response.status_code == 200
        data = response.get_json()
        assert data['markets_settled'] == 0


class TestPreviewSettlement:
    """Tests for GET /api/events/<id>/settlement-preview."""

    def test_preview_settlement_as_admin(self, full_app, test_admin, test_event, test_market, test_event_result):
        """Test previewing settlement as admin."""
        client = full_app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = test_admin.id
            sess['email'] = test_admin.email
            sess['username'] = test_admin.username
            sess['role'] = test_admin.role

        response = client.get(f'/api/events/{test_event.id}/settlement-preview')

        assert response.status_code == 200
        data = response.get_json()
        assert 'event_id' in data
        # The API returns 'previews' not 'markets'
        assert 'previews' in data
        assert isinstance(data['previews'], list)

    def test_preview_settlement_as_non_admin(self, authenticated_client, test_event):
        """Test that non-admin users cannot preview settlement."""
        response = authenticated_client.get(f'/api/events/{test_event.id}/settlement-preview')

        assert response.status_code == 403
        data = response.get_json()
        assert 'Admin access required' in data['error']

    def test_preview_settlement_unauthenticated(self, full_client, test_event):
        """Test that unauthenticated users cannot preview settlement."""
        response = full_client.get(f'/api/events/{test_event.id}/settlement-preview')

        assert response.status_code == 401
        data = response.get_json()
        assert 'Authentication required' in data['error']


class TestGetEvent:
    """Tests for GET /api/events/<id>."""

    def test_get_event_success(self, full_client, test_event):
        """Test getting event information."""
        response = full_client.get(f'/api/events/{test_event.id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['event_id'] == test_event.id
        assert data['name'] == 'Test Grand Prix'
        assert data['venue'] == 'Test Circuit'
        assert data['status'] == 'upcoming'
        assert 'start_at' in data
        assert 'season_id' in data

    def test_get_event_not_found(self, full_client):
        """Test getting non-existent event."""
        response = full_client.get('/api/events/99999')

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()
