"""Pytest configuration and fixtures."""
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from flask import Flask
from db import db
from db.models import (
    User, UserRole, Sport, League, Season, Event, Participant, Asset, Market,
    ScoringRule, Wallet, SeasonStatus, EventStatus, MarketStatus, AssetType,
    FormulaType, OTP, EventResult, ResultStatus
)
from config import create_app_config


@pytest.fixture(scope='function')
def app():
    """Create Flask app for testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False
    # Mailgun config (not actually used in tests)
    app.config['MAILGUN_API_KEY'] = None
    app.config['MAILGUN_DOMAIN'] = None
    app.config['MAILGUN_FROM_EMAIL'] = None
    # Email allowlist (None means allow all)
    app.config['OTP_ALLOWED_EMAILS'] = None

    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope='function')
def db_session(app):
    """Database session for testing."""
    with app.app_context():
        yield db.session


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email='test@example.com',
        username='testuser',
        role=UserRole.PLAYER.value
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_admin(db_session):
    """Create a test admin user."""
    admin = User(
        email='admin@example.com',
        username='admin',
        role=UserRole.ADMIN.value
    )
    db_session.add(admin)
    db_session.commit()
    return admin


@pytest.fixture
def test_sport(db_session):
    """Create a test sport."""
    sport = Sport(code='F1', name='Formula 1')
    db_session.add(sport)
    db_session.commit()
    return sport


@pytest.fixture
def test_league(db_session, test_sport):
    """Create a test league."""
    league = League(sport_id=test_sport.id, name='Formula 1')
    db_session.add(league)
    db_session.commit()
    return league


@pytest.fixture
def test_season(db_session, test_league):
    """Create a test season."""
    season = Season(
        league_id=test_league.id,
        year=2024,
        status=SeasonStatus.ACTIVE
    )
    db_session.add(season)
    db_session.commit()
    return season


@pytest.fixture
def test_event(db_session, test_season):
    """Create a test event."""
    event = Event(
        season_id=test_season.id,
        name='Test Grand Prix',
        venue='Test Circuit',
        start_at=datetime.now(timezone.utc),
        status=EventStatus.UPCOMING
    )
    db_session.add(event)
    db_session.commit()
    return event


@pytest.fixture
def test_participant(db_session, test_sport):
    """Create a test participant."""
    participant = Participant(
        sport_id=test_sport.id,
        name='Test Driver',
        short_code='TST',
        metadata_json={'team': 'Test Team'}
    )
    db_session.add(participant)
    db_session.commit()
    return participant


@pytest.fixture
def test_scoring_rule(db_session, test_sport):
    """Create a test scoring rule."""
    rule = ScoringRule(
        sport_id=test_sport.id,
        code='TEST_RULE',
        max_score=Decimal('25'),
        alpha=Decimal('1.0'),
        beta=Decimal('0.0'),
        formula_type=FormulaType.LINEAR_NORMALIZED
    )
    db_session.add(rule)
    db_session.commit()
    return rule


@pytest.fixture
def test_asset(db_session, test_participant):
    """Create a test asset."""
    asset = Asset(
        type=AssetType.PARTICIPANT,
        participant_id=test_participant.id,
        symbol='TST',
        display_name='Test Driver'
    )
    db_session.add(asset)
    db_session.commit()
    return asset


@pytest.fixture
def test_market(db_session, test_event, test_asset, test_scoring_rule):
    """Create a test market."""
    market = Market(
        event_id=test_event.id,
        asset_id=test_asset.id,
        scoring_rule_id=test_scoring_rule.id,
        market_type='outright',
        status=MarketStatus.OPEN,
        a=Decimal('1.0'),  # Bonding curve param
        b=Decimal('0.5')   # Bonding curve baseline
    )
    db_session.add(market)
    db_session.commit()
    return market


@pytest.fixture
def test_wallet(db_session, test_user):
    """Create a test wallet with balance."""
    from services.wallet_service import WalletService
    wallet = WalletService.get_or_create_wallet(test_user.id)
    # Add some balance
    from db.models import TransactionType
    from services.wallet_service import WalletService
    WalletService.add_ledger_entry(
        test_user.id,
        Decimal('1000.0'),
        TransactionType.DEPOSIT,
        description='Test deposit'
    )
    return wallet


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def full_app(app):
    """App with all blueprints registered for route testing."""
    from api import bp as main_bp
    from api.market_routes import bp as market_bp
    from api.browse_routes import bp as browse_bp
    from api.settlement_routes import bp as settlement_bp
    from auth.routes import bp as auth_bp

    # Only register if not already registered
    if 'main' not in app.blueprints:
        app.register_blueprint(main_bp)
    if 'market' not in app.blueprints:
        app.register_blueprint(market_bp)
    if 'browse' not in app.blueprints:
        app.register_blueprint(browse_bp)
    if 'settlement' not in app.blueprints:
        app.register_blueprint(settlement_bp)
    if 'auth' not in app.blueprints:
        app.register_blueprint(auth_bp, url_prefix='/auth')

    # Configure app for testing with CSRF disabled
    app.config['WTF_CSRF_ENABLED'] = False

    return app


@pytest.fixture
def full_client(full_app):
    """Flask test client with all blueprints."""
    return full_app.test_client()


@pytest.fixture
def authenticated_client(full_app, test_user):
    """Client with authenticated session."""
    client = full_app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = test_user.id
        sess['email'] = test_user.email
        sess['username'] = test_user.username
        sess['role'] = test_user.role
    return client


@pytest.fixture
def admin_client(full_app, test_admin):
    """Client with admin session."""
    client = full_app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = test_admin.id
        sess['email'] = test_admin.email
        sess['username'] = test_admin.username
        sess['role'] = test_admin.role
    return client


@pytest.fixture
def test_otp(db_session):
    """Create a valid OTP for testing.

    Uses naive datetime for SQLite compatibility - SQLite doesn't store
    timezone info, so we use naive datetimes to match what the database returns.
    """
    otp = OTP(
        email='test@example.com',
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        used=False
    )
    otp.set_code('123456')
    db_session.add(otp)
    db_session.commit()
    return otp, '123456'  # Return both OTP record and plain code


@pytest.fixture
def test_event_result(db_session, test_event, test_participant):
    """Create a test event result."""
    result = EventResult(
        event_id=test_event.id,
        participant_id=test_participant.id,
        primary_score=Decimal('25'),
        rank=1,
        status=ResultStatus.FINISHED
    )
    db_session.add(result)
    db_session.commit()
    return result


@pytest.fixture
def test_position(db_session, test_user, test_market, test_wallet):
    """Create a test position by buying shares."""
    from services.market_service import MarketService
    MarketService.buy_shares(test_user.id, test_market.id, Decimal('10.0'))
    from db.models import Position
    position = Position.query.filter_by(user_id=test_user.id, market_id=test_market.id).first()
    return position

