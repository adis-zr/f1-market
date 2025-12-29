"""Tests for ReplayService - core replay session management."""
import pytest
from decimal import Decimal
from db import db, MarketStatus
from db.replay_models import (
    ReplaySession, ReplaySessionStatus, ReplayWallet, ReplayMarket,
    ReplayPosition, ReplayLedgerEntry, ReplayDifficulty, ReplayDriverPosition
)
from services.replay_service import (
    ReplayService, ReplaySessionNotFoundError, INITIAL_BALANCE, TOTAL_RACES
)
from services.replay_ai_service import ReplayAIService


@pytest.fixture
def setup_ai_players(db_session):
    """Ensure AI players exist for tests."""
    ReplayAIService.ensure_ai_players_exist()


class TestStartReplay:
    """Tests for ReplayService.start_replay()."""

    def test_start_replay_creates_session(self, db_session, test_user, setup_ai_players):
        """Test that start_replay creates a new session."""
        state = ReplayService.start_replay(test_user.id)

        assert state['session']['user_id'] == test_user.id
        assert state['session']['status'] == 'active'
        assert state['session']['current_race'] == 0

    def test_start_replay_creates_wallet(self, db_session, test_user, setup_ai_players):
        """Test that start_replay creates wallet with initial balance."""
        state = ReplayService.start_replay(test_user.id)

        assert state['wallet']['balance'] == float(INITIAL_BALANCE)
        assert state['wallet']['locked_balance'] == 0

    def test_start_replay_creates_ledger_entry(self, db_session, test_user, setup_ai_players):
        """Test that start_replay creates initial deposit ledger entry."""
        ReplayService.start_replay(test_user.id)

        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        entries = ReplayLedgerEntry.query.filter_by(session_id=session.id).all()

        assert len(entries) == 1
        assert entries[0].amount == INITIAL_BALANCE
        assert 'Initial' in entries[0].description

    def test_start_replay_with_difficulty(self, db_session, test_user, setup_ai_players):
        """Test starting with different difficulty levels."""
        state = ReplayService.start_replay(test_user.id, ReplayDifficulty.HARD)

        assert state['session']['difficulty'] == 'hard'

    def test_start_replay_default_difficulty(self, db_session, test_user, setup_ai_players):
        """Test default difficulty is medium."""
        state = ReplayService.start_replay(test_user.id)

        assert state['session']['difficulty'] == 'medium'


class TestGetActiveSession:
    """Tests for ReplayService.get_active_session()."""

    def test_get_active_session_returns_session(self, db_session, test_user, setup_ai_players):
        """Test getting an active session."""
        ReplayService.start_replay(test_user.id)

        session = ReplayService.get_active_session(test_user.id)

        assert session is not None
        assert session.user_id == test_user.id
        assert session.status == ReplaySessionStatus.ACTIVE

    def test_get_active_session_returns_none(self, db_session, test_user):
        """Test getting session when none exists."""
        session = ReplayService.get_active_session(test_user.id)

        assert session is None

    def test_get_active_session_ignores_completed(self, db_session, test_user, setup_ai_players):
        """Test that completed sessions are not returned."""
        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        session.status = ReplaySessionStatus.COMPLETED
        db_session.commit()

        result = ReplayService.get_active_session(test_user.id)

        assert result is None


class TestGetSessionState:
    """Tests for ReplayService.get_session_state()."""

    def test_get_session_state_success(self, db_session, test_user, setup_ai_players):
        """Test getting complete session state."""
        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()

        state = ReplayService.get_session_state(session.id)

        assert 'session' in state
        assert 'wallet' in state
        assert 'positions' in state
        assert 'all_races' in state
        assert len(state['all_races']) == TOTAL_RACES

    def test_get_session_state_not_found(self, db_session):
        """Test getting state for non-existent session."""
        with pytest.raises(ReplaySessionNotFoundError):
            ReplayService.get_session_state(99999)

    def test_get_session_state_includes_markets(self, db_session, test_user, setup_ai_players):
        """Test that state includes markets when race is active."""
        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        ReplayService.advance_to_next_race(session.id)
        db_session.refresh(session)

        state = ReplayService.get_session_state(session.id)

        assert len(state['markets']) == 20  # All 20 drivers


class TestAdvanceToNextRace:
    """Tests for ReplayService.advance_to_next_race()."""

    def test_advance_from_zero(self, db_session, test_user, setup_ai_players):
        """Test advancing from race 0 to race 1."""
        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()

        result = ReplayService.advance_to_next_race(session.id)

        assert result['settlement_summary'] is None  # No settlement for first advance
        assert result['new_state']['session']['current_race'] == 1

    def test_advance_creates_markets(self, db_session, test_user, setup_ai_players):
        """Test that advancing creates markets for all drivers."""
        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()

        ReplayService.advance_to_next_race(session.id)

        markets = ReplayMarket.query.filter_by(
            session_id=session.id,
            race_number=1
        ).all()
        assert len(markets) == 20

    def test_advance_settles_previous_race(self, db_session, test_user, setup_ai_players):
        """Test that advancing settles the previous race."""
        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        ReplayService.advance_to_next_race(session.id)  # Go to race 1

        result = ReplayService.advance_to_next_race(session.id)  # Go to race 2

        assert result['settlement_summary'] is not None
        assert result['settlement_summary']['race_number'] == 1
        assert 'results' in result['settlement_summary']

    def test_advance_closes_markets(self, db_session, test_user, setup_ai_players):
        """Test that advancing closes/settles previous race markets."""
        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        ReplayService.advance_to_next_race(session.id)  # Race 1
        ReplayService.advance_to_next_race(session.id)  # Race 2

        race1_markets = ReplayMarket.query.filter_by(
            session_id=session.id,
            race_number=1
        ).all()

        assert all(m.status == MarketStatus.SETTLED for m in race1_markets)
        assert all(m.settlement_price is not None for m in race1_markets)

    def test_advance_completes_session_after_24(self, db_session, test_user, setup_ai_players):
        """Test that session completes after race 24."""
        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()

        # Advance through all 24 races + 1 more to complete
        for _ in range(25):
            ReplayService.advance_to_next_race(session.id)

        db_session.refresh(session)
        assert session.status == ReplaySessionStatus.COMPLETED
        assert session.completed_at is not None
        assert session.final_balance is not None

    def test_advance_invalid_session(self, db_session):
        """Test advancing with invalid session ID."""
        with pytest.raises(ReplaySessionNotFoundError):
            ReplayService.advance_to_next_race(99999)

    def test_advance_completed_session_fails(self, db_session, test_user, setup_ai_players):
        """Test that advancing a completed session fails."""
        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        session.status = ReplaySessionStatus.COMPLETED
        db_session.commit()

        with pytest.raises(ValueError) as exc_info:
            ReplayService.advance_to_next_race(session.id)

        assert 'not active' in str(exc_info.value).lower()


class TestSettleRace:
    """Tests for race settlement logic."""

    def test_settlement_calculates_points(self, db_session, test_user, setup_ai_players):
        """Test that settlement calculates correct points."""
        from services.replay_market_service import ReplayMarketService

        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        ReplayService.advance_to_next_race(session.id)  # Go to race 1

        # Buy shares in winner
        market = ReplayMarket.query.filter_by(
            session_id=session.id,
            race_number=1,
            driver_code='VER'  # Verstappen typically wins
        ).first()

        if market:
            ReplayMarketService.buy_shares(session.id, market.id, Decimal('5'))

        result = ReplayService.advance_to_next_race(session.id)  # Settle race 1

        # Check settlement summary
        summary = result['settlement_summary']
        assert len(summary['results']) == 20  # All drivers have results

        # Winner should have points
        winner_result = next(
            (r for r in summary['results'] if r['position'] == 1),
            None
        )
        if winner_result:
            assert winner_result['points'] > 0

    def test_settlement_includes_leaderboard(self, db_session, test_user, setup_ai_players):
        """Test that settlement includes mini leaderboard."""
        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        ReplayService.advance_to_next_race(session.id)

        result = ReplayService.advance_to_next_race(session.id)

        summary = result['settlement_summary']
        assert 'mini_leaderboard' in summary
        assert 'user_rank' in summary['mini_leaderboard']
        assert 'entries' in summary['mini_leaderboard']


class TestCreateRaceMarkets:
    """Tests for market creation logic."""

    def test_markets_have_correct_drivers(self, db_session, test_user, setup_ai_players):
        """Test that markets are created for all 20 drivers."""
        from data.f1_2024 import DRIVERS_2024

        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        ReplayService.advance_to_next_race(session.id)

        markets = ReplayMarket.query.filter_by(
            session_id=session.id,
            race_number=1
        ).all()

        driver_codes = {m.driver_code for m in markets}
        expected_codes = {d['code'] for d in DRIVERS_2024}

        assert driver_codes == expected_codes

    def test_markets_have_bonding_curve_params(self, db_session, test_user, setup_ai_players):
        """Test that markets have bonding curve parameters."""
        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        ReplayService.advance_to_next_race(session.id)

        markets = ReplayMarket.query.filter_by(session_id=session.id).all()

        for market in markets:
            assert market.a > 0
            assert market.b >= 0

    def test_markets_carry_forward_positions(self, db_session, test_user, setup_ai_players):
        """Test that positions carry forward between races."""
        from services.replay_market_service import ReplayMarketService

        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        ReplayService.advance_to_next_race(session.id)

        # Buy shares
        market = ReplayMarket.query.filter_by(
            session_id=session.id,
            race_number=1
        ).first()
        ReplayMarketService.buy_shares(session.id, market.id, Decimal('10'))

        # Advance to next race
        ReplayService.advance_to_next_race(session.id)

        # Check driver position exists
        driver_pos = ReplayDriverPosition.query.filter_by(
            session_id=session.id,
            driver_code=market.driver_code
        ).first()

        if driver_pos:
            assert driver_pos.shares > 0


class TestResetReplay:
    """Tests for ReplayService.reset_replay()."""

    def test_reset_clears_markets(self, db_session, test_user, setup_ai_players):
        """Test that reset clears all markets."""
        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        ReplayService.advance_to_next_race(session.id)

        markets_before = ReplayMarket.query.filter_by(session_id=session.id).count()
        assert markets_before > 0

        ReplayService.reset_replay(session.id)

        markets_after = ReplayMarket.query.filter_by(session_id=session.id).count()
        assert markets_after == 0

    def test_reset_restores_balance(self, db_session, test_user, setup_ai_players):
        """Test that reset restores initial balance."""
        from services.replay_market_service import ReplayMarketService

        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        ReplayService.advance_to_next_race(session.id)

        # Spend some balance
        market = ReplayMarket.query.filter_by(session_id=session.id).first()
        ReplayMarketService.buy_shares(session.id, market.id, Decimal('20'))

        wallet = ReplayWallet.query.filter_by(session_id=session.id).first()
        balance_before = wallet.balance
        assert balance_before < INITIAL_BALANCE

        # Reset
        ReplayService.reset_replay(session.id)

        db_session.refresh(wallet)
        assert wallet.balance == INITIAL_BALANCE

    def test_reset_sets_race_to_zero(self, db_session, test_user, setup_ai_players):
        """Test that reset sets current race to 0."""
        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        ReplayService.advance_to_next_race(session.id)

        assert session.current_race == 1

        ReplayService.reset_replay(session.id)

        db_session.refresh(session)
        assert session.current_race == 0

    def test_reset_clears_positions(self, db_session, test_user, setup_ai_players):
        """Test that reset clears all positions."""
        from services.replay_market_service import ReplayMarketService

        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        ReplayService.advance_to_next_race(session.id)

        market = ReplayMarket.query.filter_by(session_id=session.id).first()
        ReplayMarketService.buy_shares(session.id, market.id, Decimal('5'))

        positions_before = ReplayPosition.query.filter_by(session_id=session.id).count()
        assert positions_before > 0

        ReplayService.reset_replay(session.id)

        positions_after = ReplayPosition.query.filter_by(session_id=session.id).count()
        assert positions_after == 0

    def test_reset_invalid_session(self, db_session):
        """Test resetting invalid session."""
        with pytest.raises(ReplaySessionNotFoundError):
            ReplayService.reset_replay(99999)


class TestGetLeaderboard:
    """Tests for ReplayService.get_leaderboard()."""

    def test_leaderboard_empty_when_no_completed(self, db_session, test_user, setup_ai_players):
        """Test leaderboard when no sessions completed."""
        ReplayService.start_replay(test_user.id)

        result = ReplayService.get_leaderboard()

        # Should only have AI players or be empty of humans
        human_entries = [e for e in result['entries'] if not e.get('is_ai', True)]
        assert len(human_entries) == 0

    def test_leaderboard_includes_ai_players(self, db_session, test_user, setup_ai_players):
        """Test that leaderboard includes AI players."""
        ReplayService.start_replay(test_user.id)

        result = ReplayService.get_leaderboard(difficulty=ReplayDifficulty.MEDIUM)

        ai_entries = [e for e in result['entries'] if e.get('is_ai', False)]
        assert len(ai_entries) > 0

    def test_leaderboard_respects_limit(self, db_session, test_user, setup_ai_players):
        """Test that leaderboard respects limit parameter."""
        ReplayService.start_replay(test_user.id)

        result = ReplayService.get_leaderboard(limit=5)

        assert len(result['entries']) <= 5

    def test_leaderboard_filters_by_difficulty(self, db_session, test_user, setup_ai_players):
        """Test that leaderboard filters by difficulty."""
        result = ReplayService.get_leaderboard(difficulty=ReplayDifficulty.EASY)

        # All entries should be easy difficulty
        for entry in result['entries']:
            if 'difficulty' in entry:
                assert entry['difficulty'] == 'easy'

    def test_leaderboard_includes_user_best(self, db_session, test_user, setup_ai_players):
        """Test that leaderboard includes user's best score."""
        # Complete a session
        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()

        # Complete all races
        for _ in range(25):
            ReplayService.advance_to_next_race(session.id)

        result = ReplayService.get_leaderboard(user_id=test_user.id)

        assert result['your_best'] is not None
        assert 'final_balance' in result['your_best']


class TestGetMarketSupply:
    """Tests for internal _get_market_supply method."""

    def test_supply_starts_at_zero(self, db_session, test_user, setup_ai_players):
        """Test that market supply starts at zero."""
        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        ReplayService.advance_to_next_race(session.id)

        market = ReplayMarket.query.filter_by(session_id=session.id).first()
        supply = ReplayService._get_market_supply(market.id)

        assert supply == Decimal('0')

    def test_supply_increases_after_buy(self, db_session, test_user, setup_ai_players):
        """Test that supply increases after buying."""
        from services.replay_market_service import ReplayMarketService

        ReplayService.start_replay(test_user.id)
        session = ReplaySession.query.filter_by(user_id=test_user.id).first()
        ReplayService.advance_to_next_race(session.id)

        market = ReplayMarket.query.filter_by(session_id=session.id).first()
        ReplayMarketService.buy_shares(session.id, market.id, Decimal('10'))

        supply = ReplayService._get_market_supply(market.id)

        assert supply == Decimal('10')
