"""Replay mode database models.

These models support the "Replay 2024 Season" feature where users can
replay the F1 season in an isolated sandbox environment.
"""
import enum
from decimal import Decimal
from db.models import db, utc_now, MarketStatus, TransactionType


class ReplaySessionStatus(enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ReplayDifficulty(enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ReplaySession(db.Model):
    """A user's replay session instance.

    Each session represents an isolated sandbox where the user can
    replay the 2024 F1 season with $100 starting credit.
    """
    __tablename__ = 'replay_sessions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    current_race = db.Column(db.Integer, nullable=False, default=0)  # 0 = not started, 1-24 = race number
    status = db.Column(db.Enum(ReplaySessionStatus), nullable=False, default=ReplaySessionStatus.ACTIVE, index=True)
    difficulty = db.Column(db.Enum(ReplayDifficulty), nullable=False, default=ReplayDifficulty.MEDIUM, index=True)
    started_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    final_balance = db.Column(db.Numeric(precision=18, scale=8), nullable=True)  # Cached for leaderboard

    # Relationships
    user = db.relationship('User', backref='replay_sessions')
    wallet = db.relationship('ReplayWallet', backref='session', uselist=False, cascade='all, delete-orphan')
    markets = db.relationship('ReplayMarket', backref='session', cascade='all, delete-orphan')
    positions = db.relationship('ReplayPosition', backref='session', cascade='all, delete-orphan')
    trades = db.relationship('ReplayTrade', backref='session', cascade='all, delete-orphan')
    ledger_entries = db.relationship('ReplayLedgerEntry', backref='session', cascade='all, delete-orphan')
    driver_positions = db.relationship('ReplayDriverPosition', backref='session', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ReplaySession {self.id} user={self.user_id} race={self.current_race} status={self.status.value}>'


class ReplayWallet(db.Model):
    """Virtual wallet for a replay session.

    Starts with $100 and tracks balance changes through trading.
    """
    __tablename__ = 'replay_wallets'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('replay_sessions.id'), unique=True, nullable=False, index=True)
    balance = db.Column(db.Numeric(precision=18, scale=8), nullable=False, default=Decimal('100'))
    locked_balance = db.Column(db.Numeric(precision=18, scale=8), nullable=False, default=Decimal('0'))
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def __repr__(self):
        return f'<ReplayWallet session={self.session_id} balance={self.balance}>'


class ReplayMarket(db.Model):
    """A market for a specific driver in a specific race within a replay session.

    Each replay session has its own isolated markets, so users don't affect
    each other's prices.
    """
    __tablename__ = 'replay_markets'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('replay_sessions.id'), nullable=False, index=True)
    race_number = db.Column(db.Integer, nullable=False, index=True)
    driver_code = db.Column(db.String(10), nullable=False, index=True)  # VER, HAM, etc.
    driver_name = db.Column(db.String(100), nullable=False)
    team_name = db.Column(db.String(100), nullable=True)
    status = db.Column(db.Enum(MarketStatus), nullable=False, default=MarketStatus.OPEN, index=True)
    a = db.Column(db.Numeric(precision=18, scale=8), nullable=False)  # Bonding curve param
    b = db.Column(db.Numeric(precision=18, scale=8), nullable=False)  # Bonding curve baseline
    settlement_price = db.Column(db.Numeric(precision=18, scale=8), nullable=True)  # Points earned
    payout_per_share = db.Column(db.Numeric(precision=18, scale=8), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    # Unique constraint: one market per driver per race per session
    __table_args__ = (
        db.UniqueConstraint('session_id', 'race_number', 'driver_code', name='uq_replay_market'),
    )

    # Relationships
    positions = db.relationship('ReplayPosition', backref='market', cascade='all, delete-orphan')
    trades = db.relationship('ReplayTrade', backref='market', cascade='all, delete-orphan')
    price_history = db.relationship('ReplayPriceHistory', backref='market', cascade='all, delete-orphan', order_by='ReplayPriceHistory.timestamp.desc()')

    def __repr__(self):
        return f'<ReplayMarket {self.id} race={self.race_number} driver={self.driver_code} status={self.status.value}>'


class ReplayPosition(db.Model):
    """User's position in a replay market."""
    __tablename__ = 'replay_positions'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('replay_sessions.id'), nullable=False, index=True)
    market_id = db.Column(db.Integer, db.ForeignKey('replay_markets.id'), nullable=False, index=True)
    shares = db.Column(db.Numeric(precision=18, scale=8), nullable=False, default=Decimal('0'))
    avg_entry_price = db.Column(db.Numeric(precision=18, scale=8), nullable=False, default=Decimal('0'))
    realized_pnl = db.Column(db.Numeric(precision=18, scale=8), nullable=False, default=Decimal('0'))
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Unique constraint: one position per market per session
    __table_args__ = (
        db.UniqueConstraint('session_id', 'market_id', name='uq_replay_position'),
    )

    def __repr__(self):
        return f'<ReplayPosition session={self.session_id} market={self.market_id} shares={self.shares}>'


class ReplayTrade(db.Model):
    """A trade executed within a replay session."""
    __tablename__ = 'replay_trades'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('replay_sessions.id'), nullable=False, index=True)
    market_id = db.Column(db.Integer, db.ForeignKey('replay_markets.id'), nullable=False, index=True)
    side = db.Column(db.String(10), nullable=False)  # "buy" or "sell"
    quantity = db.Column(db.Numeric(precision=18, scale=8), nullable=False)
    price = db.Column(db.Numeric(precision=18, scale=8), nullable=False)  # Price per share at execution
    cost_or_payout = db.Column(db.Numeric(precision=18, scale=8), nullable=False)  # Total cost (buy) or payout (sell)
    executed_at = db.Column(db.DateTime, default=utc_now, nullable=False, index=True)

    def __repr__(self):
        return f'<ReplayTrade {self.id} {self.side} {self.quantity} @ {self.price}>'


class ReplayLedgerEntry(db.Model):
    """Ledger entry for audit trail within a replay session."""
    __tablename__ = 'replay_ledger_entries'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('replay_sessions.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(precision=18, scale=8), nullable=False)
    transaction_type = db.Column(db.Enum(TransactionType), nullable=False, index=True)
    reference_type = db.Column(db.String(50), nullable=True)  # "market", "race"
    reference_id = db.Column(db.Integer, nullable=True)
    description = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False, index=True)

    def __repr__(self):
        return f'<ReplayLedgerEntry {self.id} {self.transaction_type.value} {self.amount}>'


class ReplayPriceHistory(db.Model):
    """Price history for a replay market."""
    __tablename__ = 'replay_price_history'

    id = db.Column(db.Integer, primary_key=True)
    market_id = db.Column(db.Integer, db.ForeignKey('replay_markets.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=utc_now, nullable=False, index=True)
    price = db.Column(db.Numeric(precision=18, scale=8), nullable=False)
    supply = db.Column(db.Numeric(precision=18, scale=8), nullable=False, default=Decimal('0'))
    reason = db.Column(db.String(200), nullable=True)  # "buy", "sell", "settlement", "initial"
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    def __repr__(self):
        return f'<ReplayPriceHistory market={self.market_id} @ {self.timestamp}: {self.price}>'


class ReplayAIPlayer(db.Model):
    """Pre-computed AI player for leaderboard competition.

    AI players are simulated using trading strategies and provide
    competition on the leaderboard based on difficulty level.
    """
    __tablename__ = 'replay_ai_players'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.Enum(ReplayDifficulty), nullable=False, index=True)
    final_balance = db.Column(db.Numeric(precision=18, scale=8), nullable=False)
    strategy_type = db.Column(db.String(50), nullable=False)

    def __repr__(self):
        return f'<ReplayAIPlayer {self.name} difficulty={self.difficulty.value} balance={self.final_balance}>'


class ReplayDriverPosition(db.Model):
    """Season-long position in a driver across races.

    This model tracks shares held in a driver that persist across races,
    enabling the carry-forward behavior where stocks aren't sold at settlement.
    """
    __tablename__ = 'replay_driver_positions'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('replay_sessions.id'), nullable=False, index=True)
    driver_code = db.Column(db.String(10), nullable=False, index=True)
    shares = db.Column(db.Numeric(precision=18, scale=8), nullable=False, default=Decimal('0'))
    total_cost_basis = db.Column(db.Numeric(precision=18, scale=8), nullable=False, default=Decimal('0'))
    cumulative_payouts = db.Column(db.Numeric(precision=18, scale=8), nullable=False, default=Decimal('0'))
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('session_id', 'driver_code', name='uq_replay_driver_position'),
    )

    def __repr__(self):
        return f'<ReplayDriverPosition session={self.session_id} driver={self.driver_code} shares={self.shares}>'
