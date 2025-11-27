"""Pytest configuration and fixtures."""
import pytest
from decimal import Decimal
from datetime import datetime
from flask import Flask
from db import db
from db.models import (
    User, UserRole, Sport, League, Season, Event, Participant, Asset, Market,
    ScoringRule, Wallet, SeasonStatus, EventStatus, MarketStatus, AssetType,
    FormulaType
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
        start_at=datetime.utcnow(),
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

