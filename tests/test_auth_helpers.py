"""Tests for authentication helpers."""
import pytest
from flask import session
from auth.helpers import (
    get_current_user_id,
    get_current_user,
    is_admin,
    require_auth,
    require_admin,
)


class TestGetCurrentUserId:
    """Tests for get_current_user_id function."""

    def test_returns_user_id_when_authenticated(self, full_app, test_user):
        """Test that user_id is returned when session has user_id."""
        with full_app.test_request_context():
            session['user_id'] = test_user.id

            user_id = get_current_user_id()

            assert user_id == test_user.id

    def test_returns_none_when_not_authenticated(self, full_app):
        """Test that None is returned when session has no user_id."""
        with full_app.test_request_context():
            user_id = get_current_user_id()

            assert user_id is None


class TestGetCurrentUser:
    """Tests for get_current_user function."""

    def test_returns_user_when_authenticated(self, full_app, test_user):
        """Test that user object is returned when authenticated."""
        with full_app.test_request_context():
            session['user_id'] = test_user.id

            user = get_current_user()

            assert user is not None
            assert user.id == test_user.id
            assert user.email == test_user.email

    def test_returns_none_when_not_authenticated(self, full_app):
        """Test that None is returned when not authenticated."""
        with full_app.test_request_context():
            user = get_current_user()

            assert user is None


class TestIsAdmin:
    """Tests for is_admin function."""

    def test_returns_true_for_admin(self, full_app, test_admin):
        """Test that True is returned for admin user."""
        with full_app.test_request_context():
            session['user_id'] = test_admin.id

            result = is_admin()

            assert result is True

    def test_returns_false_for_regular_user(self, full_app, test_user):
        """Test that False is returned for regular user."""
        with full_app.test_request_context():
            session['user_id'] = test_user.id

            result = is_admin()

            assert result is False

    def test_returns_false_when_not_authenticated(self, full_app):
        """Test that False is returned when not authenticated."""
        with full_app.test_request_context():
            result = is_admin()

            assert result is False


class TestRequireAuthDecorator:
    """Tests for @require_auth decorator."""

    def test_allows_authenticated_request(self, authenticated_client):
        """Test that authenticated requests are allowed."""
        # Use an endpoint that requires auth
        response = authenticated_client.get('/api/portfolio')

        # Should not get 401
        assert response.status_code != 401

    def test_blocks_unauthenticated_request(self, full_client):
        """Test that unauthenticated requests are blocked."""
        response = full_client.get('/api/portfolio')

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        assert 'Authentication required' in data['error']


class TestRequireAdminDecorator:
    """Tests for @require_admin decorator."""

    def test_allows_admin_request(self, admin_client, test_event):
        """Test that admin requests are allowed."""
        response = admin_client.get(f'/api/events/{test_event.id}/settlement-preview')

        # Should not get 401 or 403
        assert response.status_code not in [401, 403]

    def test_blocks_non_admin_user(self, authenticated_client, test_event):
        """Test that non-admin requests are blocked with 403."""
        response = authenticated_client.get(f'/api/events/{test_event.id}/settlement-preview')

        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'Admin access required' in data['error']

    def test_blocks_unauthenticated_request(self, full_client, test_event):
        """Test that unauthenticated requests are blocked with 401."""
        response = full_client.get(f'/api/events/{test_event.id}/settlement-preview')

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
        assert 'Authentication required' in data['error']
