"""Tests for authentication routes."""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from db import db
from db.models import OTP, User


def make_expires_at(minutes_offset):
    """Create a timezone-naive expiration datetime for SQLite compatibility.

    SQLite doesn't store timezone info, so we use naive datetimes that match
    what the database will actually store and return.
    """
    return datetime.utcnow() + timedelta(minutes=minutes_offset)


class TestRequestOTP:
    """Tests for POST /auth/request-otp."""

    def test_request_otp_success(self, full_app):
        """Test successful OTP request."""
        client = full_app.test_client()

        response = client.post('/auth/request-otp', json={
            'email': 'test@example.com'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert data['email'] == 'test@example.com'

    def test_request_otp_missing_email(self, full_client):
        """Test OTP request with missing email."""
        response = full_client.post('/auth/request-otp', json={})

        assert response.status_code == 400
        data = response.get_json()
        assert 'Email is required' in data['message']

    def test_request_otp_invalid_email_format(self, full_client):
        """Test OTP request with invalid email format."""
        response = full_client.post('/auth/request-otp', json={
            'email': 'not-an-email'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'Invalid email format' in data['message']

    def test_request_otp_email_not_in_allowlist(self, full_app):
        """Test OTP request when email is not in allowlist."""
        # Configure email allowlist before creating client
        # The key is OTP_ALLOWED_EMAILS and must be a set
        full_app.config['OTP_ALLOWED_EMAILS'] = {'allowed@example.com'}
        client = full_app.test_client()

        response = client.post('/auth/request-otp', json={
            'email': 'notallowed@example.com'
        })

        assert response.status_code == 403
        data = response.get_json()
        assert 'not authorized' in data['message'].lower()

    def test_request_otp_mailgun_failure(self, full_app):
        """Test OTP request when Mailgun fails."""
        client = full_app.test_client()

        # Configure app for Mailgun (so it tries to send)
        full_app.config['MAILGUN_API_KEY'] = 'test-key'
        full_app.config['MAILGUN_DOMAIN'] = 'test.mailgun.org'
        full_app.config['MAILGUN_FROM_EMAIL'] = 'from@test.com'

        with patch('auth.routes.requests.post') as mock_post:
            mock_post.return_value = MagicMock(status_code=500, text='Error')

            response = client.post('/auth/request-otp', json={
                'email': 'test@example.com'
            })

            assert response.status_code == 500
            data = response.get_json()
            assert 'Failed to send OTP' in data['message']

    def test_request_otp_invalidates_existing_otps(self, full_app):
        """Test that requesting OTP invalidates existing unused OTPs."""
        client = full_app.test_client()

        with full_app.app_context():
            # Create existing OTP
            existing_otp = OTP(
                email='newtest@example.com',
                expires_at=make_expires_at(10),
                used=False
            )
            existing_otp.set_code('111111')
            db.session.add(existing_otp)
            db.session.commit()
            otp_id = existing_otp.id

        response = client.post('/auth/request-otp', json={
            'email': 'newtest@example.com'
        })

        assert response.status_code == 200

        with full_app.app_context():
            # Check existing OTP was marked as used
            refreshed_otp = db.session.get(OTP, otp_id)
            assert refreshed_otp.used is True


class TestVerifyOTP:
    """Tests for POST /auth/verify-otp."""

    def test_verify_otp_success_existing_user(self, full_app, test_user):
        """Test successful OTP verification for existing user."""
        client = full_app.test_client()

        with full_app.app_context():
            # Create OTP for existing user - use naive datetime for SQLite compatibility
            otp = OTP(
                email='test@example.com',
                expires_at=make_expires_at(10),
                used=False
            )
            otp.set_code('123456')
            db.session.add(otp)
            db.session.commit()

            response = client.post('/auth/verify-otp', json={
                'email': 'test@example.com',
                'otp': '123456'
            })

            assert response.status_code == 200
            data = response.get_json()
            assert 'Login successful' in data['message']
            assert data['email'] == 'test@example.com'

    def test_verify_otp_success_new_user(self, full_app):
        """Test successful OTP verification creates new user."""
        client = full_app.test_client()

        with full_app.app_context():
            # Create OTP for non-existent user - use naive datetime for SQLite compatibility
            otp = OTP(
                email='newuser@example.com',
                expires_at=make_expires_at(10),
                used=False
            )
            otp.set_code('654321')
            db.session.add(otp)
            db.session.commit()

            response = client.post('/auth/verify-otp', json={
                'email': 'newuser@example.com',
                'otp': '654321'
            })

            assert response.status_code == 200
            data = response.get_json()
            assert 'Login successful' in data['message']

            # Check user was created
            user = User.query.filter_by(email='newuser@example.com').first()
            assert user is not None
            assert user.username == 'newuser'

    def test_verify_otp_missing_fields(self, full_client):
        """Test OTP verification with missing fields."""
        response = full_client.post('/auth/verify-otp', json={
            'email': 'test@example.com'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'required' in data['message'].lower()

    def test_verify_otp_invalid_code(self, full_app):
        """Test OTP verification with wrong code."""
        client = full_app.test_client()

        with full_app.app_context():
            otp = OTP(
                email='wrongcode@example.com',
                expires_at=make_expires_at(10),
                used=False
            )
            otp.set_code('123456')
            db.session.add(otp)
            db.session.commit()

            response = client.post('/auth/verify-otp', json={
                'email': 'wrongcode@example.com',
                'otp': '000000'  # Wrong code
            })

            assert response.status_code == 401
            data = response.get_json()
            assert 'Invalid or expired' in data['message']

    def test_verify_otp_expired(self, full_app):
        """Test OTP verification with expired OTP."""
        client = full_app.test_client()

        with full_app.app_context():
            # Create expired OTP - use naive datetime for SQLite compatibility
            otp = OTP(
                email='expiredtest@example.com',
                expires_at=make_expires_at(-1),  # Expired
                used=False
            )
            otp.set_code('999999')
            db.session.add(otp)
            db.session.commit()

            response = client.post('/auth/verify-otp', json={
                'email': 'expiredtest@example.com',
                'otp': '999999'
            })

            assert response.status_code == 401
            data = response.get_json()
            assert 'Invalid or expired' in data['message']

    def test_verify_otp_already_used(self, full_app):
        """Test OTP verification with already used OTP."""
        client = full_app.test_client()

        with full_app.app_context():
            # Create used OTP - use naive datetime for SQLite compatibility
            otp = OTP(
                email='usedtest@example.com',
                expires_at=make_expires_at(10),
                used=True  # Already used
            )
            otp.set_code('888888')
            db.session.add(otp)
            db.session.commit()

        response = client.post('/auth/verify-otp', json={
            'email': 'usedtest@example.com',
            'otp': '888888'
        })

        assert response.status_code == 401
        data = response.get_json()
        assert 'Invalid or expired' in data['message']

    def test_verify_otp_creates_session(self, full_app, test_user):
        """Test that successful verification creates session."""
        client = full_app.test_client()

        with full_app.app_context():
            otp = OTP(
                email='test@example.com',
                expires_at=make_expires_at(10),
                used=False
            )
            otp.set_code('111111')
            db.session.add(otp)
            db.session.commit()

            response = client.post('/auth/verify-otp', json={
                'email': 'test@example.com',
                'otp': '111111'
            })

            assert response.status_code == 200

            # Check session by calling /auth/me
            me_response = client.get('/auth/me')
            me_data = me_response.get_json()
            assert me_data['logged_in'] is True
            assert me_data['email'] == 'test@example.com'


class TestGetCurrentUser:
    """Tests for GET /auth/me."""

    def test_get_current_user_authenticated(self, authenticated_client, test_user):
        """Test getting current user when authenticated."""
        response = authenticated_client.get('/auth/me')

        assert response.status_code == 200
        data = response.get_json()
        assert data['logged_in'] is True
        assert data['email'] == test_user.email
        assert data['username'] == test_user.username

    def test_get_current_user_not_authenticated(self, full_client):
        """Test getting current user when not authenticated."""
        response = full_client.get('/auth/me')

        assert response.status_code == 200
        data = response.get_json()
        assert data['logged_in'] is False


class TestLogout:
    """Tests for POST /auth/logout."""

    def test_logout_clears_session(self, authenticated_client):
        """Test that logout clears the session."""
        # First verify we're logged in
        me_response = authenticated_client.get('/auth/me')
        assert me_response.get_json()['logged_in'] is True

        # Logout
        logout_response = authenticated_client.post('/auth/logout')
        assert logout_response.status_code == 200
        assert 'Logged out successfully' in logout_response.get_json()['message']

        # Verify we're logged out
        me_response = authenticated_client.get('/auth/me')
        assert me_response.get_json()['logged_in'] is False


class TestCSRFToken:
    """Tests for GET /auth/csrf-token."""

    def test_get_csrf_token(self, full_client):
        """Test getting CSRF token."""
        response = full_client.get('/auth/csrf-token')

        assert response.status_code == 200
        data = response.get_json()
        assert 'csrf_token' in data
        assert len(data['csrf_token']) > 0
