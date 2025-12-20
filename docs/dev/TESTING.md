# Testing Guide

This guide covers running tests, understanding the test suite, and writing new tests.

## Quick Reference

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_pricing.py -v

# Run specific test
pytest tests/test_pricing.py::test_buy_price -v

# Run with coverage
pytest --cov=. --cov-report=html

# Run only fast tests (exclude slow integration tests)
pytest -m "not slow"
```

---

## Test Framework

The project uses **pytest** with the following setup:

| Component | Purpose |
|-----------|---------|
| pytest | Test framework |
| pytest-cov | Coverage reporting |
| conftest.py | Shared fixtures |
| In-memory SQLite | Test database |

---

## Running Tests

### Run All Tests

```bash
pytest
```

### Verbose Output

```bash
pytest -v
```

Shows individual test names and results:

```
tests/test_pricing.py::test_price_at_zero_supply PASSED
tests/test_pricing.py::test_price_increases_with_supply PASSED
tests/test_pricing.py::test_buy_cost PASSED
...
```

### Run Specific File

```bash
pytest tests/test_pricing.py -v
```

### Run Specific Test

```bash
pytest tests/test_pricing.py::test_buy_price -v
```

### Run by Keyword

```bash
# Run all tests with "buy" in the name
pytest -k buy -v

# Run all tests with "market" but not "settlement"
pytest -k "market and not settlement" -v
```

### Coverage Report

```bash
# Generate coverage report
pytest --cov=. --cov-report=html

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Watch Mode

Use pytest-watch for automatic re-runs (install separately):

```bash
pip install pytest-watch
ptw  # Watches for changes and re-runs tests
```

---

## Test Suite Overview

```
tests/
├── conftest.py              # Shared fixtures
├── test_pricing.py          # Bonding curve math
├── test_market_service.py   # Buy/sell logic
├── test_wallet_service.py   # Balance operations
├── test_scoring.py          # Settlement formulas
├── test_settlement.py       # Settlement flow
├── test_auth_routes.py      # OTP authentication
├── test_auth_helpers.py     # Auth utilities
├── test_market_routes.py    # Trading API endpoints
├── test_browse_routes.py    # Read-only endpoints
└── test_settlement_routes.py # Settlement endpoints
```

### Test Categories

| Category | Files | What They Test |
|----------|-------|----------------|
| **Unit** | `test_pricing.py`, `test_scoring.py` | Pure functions, math |
| **Service** | `test_market_service.py`, `test_wallet_service.py`, `test_settlement.py` | Business logic |
| **Route** | `test_*_routes.py` | API endpoints |
| **Auth** | `test_auth_routes.py`, `test_auth_helpers.py` | Authentication |

---

## Fixtures

All fixtures are defined in `tests/conftest.py`. Understanding them is key to writing tests.

### Database Fixtures

```python
@pytest.fixture
def app():
    """Flask app with in-memory SQLite database."""
    # Creates fresh database for each test
    # Auto-teardown after test completes

@pytest.fixture
def db_session(app):
    """Database session for direct DB operations."""
```

### Model Fixtures

These create test data and are designed to work together:

```python
@pytest.fixture
def test_user(db_session):
    """Create a test user (PLAYER role)."""

@pytest.fixture
def test_admin(db_session):
    """Create a test admin user (ADMIN role)."""

@pytest.fixture
def test_sport(db_session):
    """Create F1 sport."""

@pytest.fixture
def test_league(db_session, test_sport):
    """Create league (depends on sport)."""

@pytest.fixture
def test_season(db_session, test_league):
    """Create season (depends on league)."""

@pytest.fixture
def test_event(db_session, test_season):
    """Create event (depends on season)."""

@pytest.fixture
def test_participant(db_session, test_sport):
    """Create test driver."""

@pytest.fixture
def test_asset(db_session, test_participant):
    """Create tradeable asset for participant."""

@pytest.fixture
def test_scoring_rule(db_session, test_sport):
    """Create scoring rule for settlement."""

@pytest.fixture
def test_market(db_session, test_event, test_asset, test_scoring_rule):
    """Create market with bonding curve params a=1.0, b=0.5."""

@pytest.fixture
def test_wallet(db_session, test_user):
    """Create wallet with 1000 balance."""

@pytest.fixture
def test_position(db_session, test_user, test_market, test_wallet):
    """Create position by buying 10 shares."""
```

### Client Fixtures

For testing HTTP endpoints:

```python
@pytest.fixture
def client(app):
    """Basic Flask test client."""

@pytest.fixture
def full_client(full_app):
    """Client with all blueprints registered."""

@pytest.fixture
def authenticated_client(full_app, test_user):
    """Client with user session (logged in as PLAYER)."""

@pytest.fixture
def admin_client(full_app, test_admin):
    """Client with admin session (logged in as ADMIN)."""
```

### Using Fixtures

Fixtures are used by including them as test function parameters:

```python
def test_buy_shares(test_user, test_market, test_wallet):
    """Test buying shares in a market."""
    # test_user, test_market, test_wallet are automatically created
    # and available for use
    result = MarketService.buy_shares(
        test_user.id,
        test_market.id,
        Decimal('10.0')
    )
    assert result['shares'] == 10
```

---

## Writing Tests

### Basic Test Structure

```python
# tests/test_example.py

from decimal import Decimal
import pytest

def test_something_simple():
    """Test description."""
    # Arrange
    value = Decimal('10.0')

    # Act
    result = value * 2

    # Assert
    assert result == Decimal('20.0')


def test_with_fixtures(test_user, test_market, test_wallet):
    """Test using fixtures."""
    # Fixtures are passed as parameters
    assert test_user.email == 'test@example.com'
    assert test_wallet.balance == Decimal('1000.0')


def test_expected_exception():
    """Test that an exception is raised."""
    with pytest.raises(ValueError) as exc_info:
        raise ValueError("Invalid input")

    assert "Invalid" in str(exc_info.value)


class TestMarketOperations:
    """Group related tests in a class."""

    def test_buy(self, test_user, test_market, test_wallet):
        """Test buying shares."""
        pass

    def test_sell(self, test_position):
        """Test selling shares."""
        pass
```

### Testing Services

```python
# tests/test_market_service.py

from decimal import Decimal
from services.market_service import MarketService


def test_buy_shares(test_user, test_market, test_wallet):
    """Test buying shares in a market."""
    # Act
    result = MarketService.buy_shares(
        test_user.id,
        test_market.id,
        Decimal('10.0')
    )

    # Assert
    assert result['shares'] == Decimal('10.0')
    assert result['cost'] > 0
    assert result['new_price'] > 0


def test_sell_shares(test_position):
    """Test selling shares from a position."""
    # test_position already has shares
    user_id = test_position.user_id
    market_id = test_position.market_id
    shares = test_position.shares

    result = MarketService.sell_shares(
        user_id,
        market_id,
        shares / 2  # Sell half
    )

    assert result['shares_sold'] == shares / 2
    assert result['payout'] > 0


def test_buy_insufficient_funds(test_user, test_market):
    """Test buying with no wallet balance fails."""
    # No test_wallet fixture = no balance
    with pytest.raises(ValueError) as exc_info:
        MarketService.buy_shares(
            test_user.id,
            test_market.id,
            Decimal('10.0')
        )

    assert "Insufficient" in str(exc_info.value)
```

### Testing Routes

```python
# tests/test_market_routes.py

import json


def test_get_market(full_client, test_market):
    """Test GET /api/markets/<id>."""
    response = full_client.get(f'/api/markets/{test_market.id}')

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['id'] == test_market.id
    assert 'price' in data


def test_buy_shares_requires_auth(full_client, test_market):
    """Test that buying requires authentication."""
    response = full_client.post(
        f'/api/markets/{test_market.id}/buy',
        json={'quantity': 10}
    )

    assert response.status_code == 401


def test_buy_shares_authenticated(authenticated_client, test_market, test_wallet):
    """Test buying shares when authenticated."""
    response = authenticated_client.post(
        f'/api/markets/{test_market.id}/buy',
        json={'quantity': 10}
    )

    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'cost' in data
    assert data['shares'] == 10


def test_admin_only_endpoint(authenticated_client, admin_client, test_event):
    """Test that settlement requires admin role."""
    # Regular user can't settle
    response = authenticated_client.post(f'/api/events/{test_event.id}/settle')
    assert response.status_code == 403

    # Admin can settle
    response = admin_client.post(f'/api/events/{test_event.id}/settle')
    # May fail for other reasons, but not 403
    assert response.status_code != 403
```

### Testing with Mocks

```python
# tests/test_with_mocks.py

from unittest.mock import patch, MagicMock


def test_external_api_call(full_client, authenticated_client):
    """Test endpoint that calls external API."""
    mock_response = {
        'driver_standings': [
            {'position': 1, 'driver_name': 'Max Verstappen'}
        ]
    }

    with patch('f1.client.SportMonksClient.get_standings') as mock:
        mock.return_value = mock_response

        response = authenticated_client.get('/api/f1/standings')

        assert response.status_code == 200
        mock.assert_called_once()
```

---

## Test Database

### In-Memory SQLite

Tests use an in-memory SQLite database:

```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
```

Benefits:
- Fast (no disk I/O)
- Isolated (fresh database per test)
- No cleanup needed

### Fresh Database Per Test

Each test function gets a fresh database:

```python
@pytest.fixture(scope='function')  # Default scope
def app():
    # Create app
    with app.app_context():
        db.create_all()    # Create tables
        yield app
        db.drop_all()      # Drop tables after test
```

### Committing Data

Fixtures that create data must commit:

```python
@pytest.fixture
def test_user(db_session):
    user = User(email='test@example.com')
    db_session.add(user)
    db_session.commit()  # Must commit!
    return user
```

---

## F1 API Integration Testing

For testing the F1 API integration (SportMonks), see manual testing below.

### Start Server

```bash
python app.py
```

### Test Endpoints Manually

```bash
# Get CSRF token (for session)
curl -X GET http://localhost:5000/auth/csrf-token -c cookies.txt

# Request OTP
curl -X POST http://localhost:5000/auth/request-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@example.com"}' \
  -b cookies.txt -c cookies.txt

# Check console for OTP code, then verify
curl -X POST http://localhost:5000/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"email": "your-email@example.com", "otp": "123456"}' \
  -b cookies.txt -c cookies.txt

# Test F1 endpoints (requires auth)
curl -X GET http://localhost:5000/api/f1/standings -b cookies.txt
curl -X GET http://localhost:5000/api/f1/race-status -b cookies.txt
```

### F1 API Test Script

```bash
python test_f1_api.py
```

This script:
1. Requests an OTP
2. Verifies the OTP
3. Tests all F1 endpoints
4. Verifies authentication is required

---

## Debugging Tests

### Print Debug Info

```python
def test_something(capsys):
    """Use print for debugging."""
    print("Debug info here")
    assert True

    # View output
    captured = capsys.readouterr()
    print(captured.out)
```

### Run Single Test with Output

```bash
pytest tests/test_pricing.py::test_buy_price -v -s
```

The `-s` flag shows print output.

### Use pytest.set_trace()

```python
def test_with_debugger():
    """Drop into debugger."""
    x = 10
    import pytest; pytest.set_trace()  # Debugger stops here
    assert x == 10
```

### Verbose Failure Info

```bash
pytest --tb=long  # Full traceback
pytest --tb=short  # Short traceback
```

---

## Test Configuration

### pytest.ini

Create `pytest.ini` in project root for default options:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
markers =
    slow: marks tests as slow
    integration: marks integration tests
```

### Skip Slow Tests

Mark slow tests:

```python
@pytest.mark.slow
def test_slow_operation():
    """This test takes a while."""
    time.sleep(10)
```

Run without slow tests:

```bash
pytest -m "not slow"
```

---

## Troubleshooting

### Fixture Not Found

```
fixture 'test_market' not found
```

Check that:
1. The fixture is defined in `conftest.py`
2. The fixture name is spelled correctly
3. The test file is in the `tests/` directory

### Database Errors

```
sqlalchemy.exc.OperationalError: no such table
```

Ensure:
1. You're using the `app` or `db_session` fixture
2. Tables are created with `db.create_all()`
3. The fixture scope is correct

### Session/Auth Issues

For testing authenticated endpoints:

```python
# Use authenticated_client fixture
def test_protected_endpoint(authenticated_client):
    response = authenticated_client.get('/api/protected')
    assert response.status_code == 200
```

### CSRF Errors

CSRF is disabled in tests:

```python
app.config['WTF_CSRF_ENABLED'] = False
```

If you still see CSRF errors, ensure you're using the `full_client` or `authenticated_client` fixture.

---

## Next Steps

- [Setup Guide](SETUP.md) - Development setup
- [Architecture Guide](ARCHITECTURE.md) - System design
- [API Reference](API_REFERENCE.md) - Endpoint documentation
