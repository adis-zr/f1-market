"""Pytest fixtures for F1 2024 season simulation."""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from flask import Flask
from typing import Dict, List

from db import db
from db.models import (
    User, UserRole, Sport, League, Season, Event, Participant, Asset, Market,
    ScoringRule, Wallet, SeasonStatus, EventStatus, MarketStatus, AssetType,
    FormulaType, EventResult, ResultStatus, TransactionType
)
from services.wallet_service import WalletService

from .data.drivers import DRIVERS_2024
from .data.races import RACES_2024
from .data.points import get_points_for_position
from .strategies import (
    WinnerPredictorStrategy, ValueHunterStrategy, MomentumTraderStrategy,
    RandomTraderStrategy, DiversifiedTraderStrategy,
    BackmarkerFanStrategy, BadTimingStrategy, ChaseHypeStrategy
)
from .helpers.snapshot import SnapshotCapture


# Simulation constants
BONDING_A = Decimal('0.1')  # Bonding curve slope
BONDING_B = Decimal('0.5')  # Bonding curve baseline
INITIAL_BALANCE = Decimal('100')  # Starting credits per user
NUM_USERS = 10


@pytest.fixture(scope='function')
def simulation_app():
    """Create Flask app for simulation testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'simulation-test-key'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['MAILGUN_API_KEY'] = None
    app.config['MAILGUN_DOMAIN'] = None
    app.config['MAILGUN_FROM_EMAIL'] = None
    app.config['OTP_ALLOWED_EMAILS'] = None

    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def simulation_setup(simulation_app):
    """Set up complete simulation environment.

    Creates:
    - Sport, League, Season
    - Scoring rule
    - 20 drivers as Participants with Assets
    - 10 users with 100 credits each
    - Returns dict with all created entities
    """
    with simulation_app.app_context():
        # Create sport
        sport = Sport(code='F1', name='Formula 1')
        db.session.add(sport)
        db.session.flush()

        # Create league
        league = League(sport_id=sport.id, name='F1 World Championship')
        db.session.add(league)
        db.session.flush()

        # Create season
        season = Season(
            league_id=league.id,
            year=2024,
            status=SeasonStatus.ACTIVE
        )
        db.session.add(season)
        db.session.flush()

        # Create scoring rule (F1 standard)
        scoring_rule = ScoringRule(
            sport_id=sport.id,
            code='F1_2024',
            max_score=Decimal('25'),
            alpha=Decimal('1.0'),
            beta=Decimal('0.0'),
            formula_type=FormulaType.LINEAR_NORMALIZED
        )
        db.session.add(scoring_rule)
        db.session.flush()

        # Create drivers and assets
        drivers = {}  # driver_code -> {participant, asset}
        for driver_info in DRIVERS_2024:
            participant = Participant(
                sport_id=sport.id,
                name=driver_info['name'],
                short_code=driver_info['code'],
                metadata_json={'team': driver_info['team'], 'number': driver_info['number']}
            )
            db.session.add(participant)
            db.session.flush()

            asset = Asset(
                type=AssetType.PARTICIPANT,
                participant_id=participant.id,
                symbol=driver_info['code'],
                display_name=driver_info['name']
            )
            db.session.add(asset)
            db.session.flush()

            drivers[driver_info['code']] = {
                'participant': participant,
                'asset': asset
            }

        # Create 10 users with wallets
        users = {}  # user_index (0-9) -> User
        for i in range(NUM_USERS):
            user = User(
                email=f'user{i}@simulation.test',
                username=f'user{i}',
                role=UserRole.PLAYER.value
            )
            db.session.add(user)
            db.session.flush()

            # Create wallet with initial balance
            wallet = WalletService.get_or_create_wallet(user.id)
            WalletService.add_ledger_entry(
                user.id,
                INITIAL_BALANCE,
                TransactionType.DEPOSIT,
                description='Initial simulation credits'
            )

            users[i] = user

        db.session.commit()

        yield {
            'app': simulation_app,
            'sport': sport,
            'league': league,
            'season': season,
            'scoring_rule': scoring_rule,
            'drivers': drivers,
            'users': users,
        }


@pytest.fixture
def create_race_event(simulation_setup):
    """Factory fixture to create race events with markets.

    Returns a function that creates an event for a specific race
    with markets for all 20 drivers.
    """
    def _create_race_event(race_num: int) -> Dict:
        race_info = RACES_2024.get(race_num)
        if not race_info:
            raise ValueError(f"Race {race_num} not found")

        season = simulation_setup['season']
        scoring_rule = simulation_setup['scoring_rule']
        drivers = simulation_setup['drivers']

        # Create event
        event = Event(
            season_id=season.id,
            name=race_info['name'],
            venue=race_info['venue'],
            start_at=datetime.fromisoformat(race_info['date'] + 'T14:00:00+00:00'),
            status=EventStatus.UPCOMING
        )
        db.session.add(event)
        db.session.flush()

        # Create markets for all drivers
        markets = {}  # driver_code -> Market
        for driver_code, driver_data in drivers.items():
            market = Market(
                event_id=event.id,
                asset_id=driver_data['asset'].id,
                scoring_rule_id=scoring_rule.id,
                market_type='outright',
                status=MarketStatus.OPEN,
                a=BONDING_A,
                b=BONDING_B
            )
            db.session.add(market)
            db.session.flush()
            markets[driver_code] = market

        db.session.commit()

        return {
            'event': event,
            'markets': markets,
            'race_info': race_info
        }

    return _create_race_event


@pytest.fixture
def create_event_results(simulation_setup):
    """Factory fixture to create event results from race data.

    Returns a function that creates EventResult records for a race.
    """
    def _create_event_results(event, race_num: int) -> List[EventResult]:
        race_info = RACES_2024.get(race_num)
        if not race_info:
            raise ValueError(f"Race {race_num} not found")

        drivers = simulation_setup['drivers']
        results = []

        for driver_code, position in race_info['results']:
            if driver_code not in drivers:
                continue

            participant = drivers[driver_code]['participant']
            points = get_points_for_position(position)

            # Determine status
            if position == 0:
                status = ResultStatus.DNF
            else:
                status = ResultStatus.FINISHED

            result = EventResult(
                event_id=event.id,
                participant_id=participant.id,
                primary_score=points,
                rank=position if position > 0 else None,
                status=status
            )
            db.session.add(result)
            results.append(result)

        db.session.commit()
        return results

    return _create_event_results


@pytest.fixture
def user_strategies(simulation_setup):
    """Create trading strategies for all 10 users.

    Distribution:
    - Users 0-2: Profitable strategies
    - Users 3-6: Break-even strategies
    - Users 7-9: Losing strategies
    """
    users = simulation_setup['users']

    strategies = {
        # Profitable (users 0-2)
        0: WinnerPredictorStrategy(users[0].id),
        1: ValueHunterStrategy(users[1].id),
        2: MomentumTraderStrategy(users[2].id),

        # Break-even (users 3-6)
        3: RandomTraderStrategy(users[3].id, seed=42),
        4: RandomTraderStrategy(users[4].id, seed=123),
        5: DiversifiedTraderStrategy(users[5].id, variant=0),
        6: DiversifiedTraderStrategy(users[6].id, variant=1),

        # Losing (users 7-9)
        7: BackmarkerFanStrategy(users[7].id),
        8: BadTimingStrategy(users[8].id),
        9: ChaseHypeStrategy(users[9].id),
    }

    return strategies


@pytest.fixture
def snapshot_capture(simulation_app):
    """Create snapshot capture utility."""
    return SnapshotCapture(simulation_app)


def get_user_positions_by_driver(user_id: int, markets: Dict) -> Dict[str, Decimal]:
    """Get user's positions indexed by driver code.

    Args:
        user_id: User ID
        markets: Dict of driver_code -> Market

    Returns:
        Dict of driver_code -> shares held
    """
    from db.models import Position

    positions = {}
    for driver_code, market in markets.items():
        pos = Position.query.filter_by(
            user_id=user_id,
            market_id=market.id
        ).first()
        if pos and pos.shares > 0:
            positions[driver_code] = Decimal(str(pos.shares))

    return positions
