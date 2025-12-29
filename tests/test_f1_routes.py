"""Tests for F1 API routes."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def f1_app(full_app):
    """App with F1 blueprint registered."""
    from api.f1_routes import bp as f1_bp

    if 'f1' not in full_app.blueprints:
        full_app.register_blueprint(f1_bp)

    # Configure F1 settings
    full_app.config['F1_PROVIDER'] = 'sportmonks'
    full_app.config['F1_CURRENT_SEASON'] = 2024

    return full_app


@pytest.fixture
def f1_client(f1_app):
    """Client for F1 routes."""
    return f1_app.test_client()


@pytest.fixture
def authenticated_f1_client(f1_app, test_user):
    """Authenticated client for F1 routes."""
    client = f1_app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
        sess['email'] = test_user.email
        sess['username'] = test_user.username
        sess['role'] = test_user.role
    return client


@pytest.fixture
def mock_f1_service():
    """Mock F1Service for testing."""
    with patch('api.f1_routes.get_f1_service') as mock:
        service = MagicMock()
        mock.return_value = service
        yield service


# =============================================================================
# Standings Tests
# =============================================================================

class TestGetStandings:
    """Tests for GET /api/f1/standings."""

    def test_get_standings_success(self, authenticated_f1_client, mock_f1_service):
        """Test getting standings successfully."""
        mock_f1_service.get_driver_standings.return_value = [
            {'position': 1, 'driver': 'VER', 'points': 400},
            {'position': 2, 'driver': 'NOR', 'points': 300},
        ]
        mock_f1_service.get_constructor_standings.return_value = [
            {'position': 1, 'team': 'Red Bull', 'points': 700},
            {'position': 2, 'team': 'McLaren', 'points': 600},
        ]

        response = authenticated_f1_client.get('/api/f1/standings')

        assert response.status_code == 200
        data = response.get_json()
        assert 'driver_standings' in data
        assert 'constructor_standings' in data
        assert len(data['driver_standings']) == 2
        assert len(data['constructor_standings']) == 2

    def test_get_standings_with_season(self, authenticated_f1_client, mock_f1_service):
        """Test getting standings for specific season."""
        mock_f1_service.get_driver_standings.return_value = []
        mock_f1_service.get_constructor_standings.return_value = []

        response = authenticated_f1_client.get('/api/f1/standings?season=2023')

        assert response.status_code == 200
        mock_f1_service.get_driver_standings.assert_called_with(season=2023)
        mock_f1_service.get_constructor_standings.assert_called_with(season=2023)

    def test_get_standings_api_failure(self, authenticated_f1_client, mock_f1_service):
        """Test standings when API fails."""
        mock_f1_service.get_driver_standings.return_value = None
        mock_f1_service.get_constructor_standings.return_value = None

        response = authenticated_f1_client.get('/api/f1/standings')

        assert response.status_code == 503
        data = response.get_json()
        assert 'Failed to fetch' in data['message']

    def test_get_standings_unauthenticated(self, f1_client, mock_f1_service):
        """Test standings without authentication."""
        response = f1_client.get('/api/f1/standings')

        assert response.status_code == 401

    def test_get_standings_server_error(self, authenticated_f1_client, mock_f1_service):
        """Test standings with server error."""
        mock_f1_service.get_driver_standings.side_effect = Exception("API error")

        response = authenticated_f1_client.get('/api/f1/standings')

        assert response.status_code == 500
        data = response.get_json()
        assert 'Server error' in data['message']


# =============================================================================
# Race Status Tests
# =============================================================================

class TestGetRaceStatus:
    """Tests for GET /api/f1/race-status."""

    def test_race_ongoing(self, authenticated_f1_client, mock_f1_service):
        """Test when race is ongoing."""
        mock_f1_service.is_race_ongoing.return_value = True
        mock_f1_service.get_current_session_key.return_value = 12345

        response = authenticated_f1_client.get('/api/f1/race-status')

        assert response.status_code == 200
        data = response.get_json()
        assert data['race_ongoing'] is True
        assert data['race_id'] == 12345

    def test_race_not_ongoing(self, authenticated_f1_client, mock_f1_service):
        """Test when no race is ongoing."""
        mock_f1_service.is_race_ongoing.return_value = False

        response = authenticated_f1_client.get('/api/f1/race-status')

        assert response.status_code == 200
        data = response.get_json()
        assert data['race_ongoing'] is False
        assert 'race_id' not in data

    def test_race_status_unauthenticated(self, f1_client, mock_f1_service):
        """Test race status without authentication."""
        response = f1_client.get('/api/f1/race-status')

        assert response.status_code == 401

    def test_race_status_server_error(self, authenticated_f1_client, mock_f1_service):
        """Test race status with server error."""
        mock_f1_service.is_race_ongoing.side_effect = Exception("API error")

        response = authenticated_f1_client.get('/api/f1/race-status')

        assert response.status_code == 500


# =============================================================================
# Telemetry Tests
# =============================================================================

class TestGetTelemetry:
    """Tests for GET /api/f1/telemetry."""

    def test_get_telemetry_success(self, authenticated_f1_client, mock_f1_service):
        """Test getting telemetry successfully."""
        mock_f1_service.get_telemetry.return_value = {
            'positions': [
                {'position': 1, 'driver': 'VER', 'gap': 0},
                {'position': 2, 'driver': 'NOR', 'gap': 5.2},
            ],
            'lap': 45,
        }

        response = authenticated_f1_client.get('/api/f1/telemetry?race_id=12345')

        assert response.status_code == 200
        data = response.get_json()
        assert 'positions' in data
        assert data['lap'] == 45

    def test_get_telemetry_with_session_key(self, authenticated_f1_client, mock_f1_service):
        """Test telemetry with session_key parameter."""
        mock_f1_service.get_telemetry.return_value = {'positions': []}

        response = authenticated_f1_client.get('/api/f1/telemetry?session_key=12345')

        assert response.status_code == 200
        mock_f1_service.get_telemetry.assert_called_with(session_key=12345)

    def test_get_telemetry_no_race_ongoing(self, authenticated_f1_client, mock_f1_service):
        """Test telemetry when no race is ongoing."""
        mock_f1_service.get_telemetry.return_value = None
        mock_f1_service.is_race_ongoing.return_value = False

        response = authenticated_f1_client.get('/api/f1/telemetry')

        assert response.status_code == 404
        data = response.get_json()
        assert 'No race is currently ongoing' in data['message']
        assert data['race_ongoing'] is False

    def test_get_telemetry_api_failure(self, authenticated_f1_client, mock_f1_service):
        """Test telemetry when API fails but race is ongoing."""
        mock_f1_service.get_telemetry.return_value = None
        mock_f1_service.is_race_ongoing.return_value = True

        response = authenticated_f1_client.get('/api/f1/telemetry')

        assert response.status_code == 503
        data = response.get_json()
        assert 'Failed to fetch telemetry' in data['message']
        assert data['race_ongoing'] is True

    def test_get_telemetry_unauthenticated(self, f1_client, mock_f1_service):
        """Test telemetry without authentication."""
        response = f1_client.get('/api/f1/telemetry')

        assert response.status_code == 401

    def test_get_telemetry_server_error(self, authenticated_f1_client, mock_f1_service):
        """Test telemetry with server error."""
        mock_f1_service.get_telemetry.side_effect = Exception("API error")

        response = authenticated_f1_client.get('/api/f1/telemetry')

        assert response.status_code == 500


# =============================================================================
# Last Race Tests
# =============================================================================

class TestGetLastRace:
    """Tests for GET /api/f1/last-race."""

    def test_get_last_race_success(self, authenticated_f1_client, mock_f1_service):
        """Test getting last race successfully."""
        mock_f1_service.get_last_race_results.return_value = {
            'race_name': 'Monaco Grand Prix',
            'date': '2024-05-26',
            'results': [
                {'position': 1, 'driver': 'LEC', 'points': 25},
                {'position': 2, 'driver': 'SAI', 'points': 18},
            ]
        }

        response = authenticated_f1_client.get('/api/f1/last-race')

        assert response.status_code == 200
        data = response.get_json()
        assert data['race_found'] is True
        assert data['race_name'] == 'Monaco Grand Prix'
        assert len(data['results']) == 2

    def test_get_last_race_with_season(self, authenticated_f1_client, mock_f1_service):
        """Test getting last race for specific season."""
        mock_f1_service.get_last_race_results.return_value = {
            'race_name': 'Abu Dhabi GP',
            'results': []
        }

        response = authenticated_f1_client.get('/api/f1/last-race?season=2023')

        assert response.status_code == 200
        mock_f1_service.get_last_race_results.assert_called_with(season_year=2023)

    def test_get_last_race_not_found(self, authenticated_f1_client, mock_f1_service):
        """Test when no finished race found."""
        mock_f1_service.get_last_race_results.return_value = None

        response = authenticated_f1_client.get('/api/f1/last-race')

        assert response.status_code == 404
        data = response.get_json()
        assert data['race_found'] is False
        assert 'No finished race found' in data['message']

    def test_get_last_race_unauthenticated(self, f1_client, mock_f1_service):
        """Test last race without authentication."""
        response = f1_client.get('/api/f1/last-race')

        assert response.status_code == 401

    def test_get_last_race_server_error(self, authenticated_f1_client, mock_f1_service):
        """Test last race with server error."""
        mock_f1_service.get_last_race_results.side_effect = Exception("API error")

        response = authenticated_f1_client.get('/api/f1/last-race')

        assert response.status_code == 500
