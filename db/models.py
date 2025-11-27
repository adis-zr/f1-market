"""Database models."""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import enum
from decimal import Decimal
from passlib.context import CryptContext

db = SQLAlchemy()
otp_context = CryptContext(schemes=["argon2"], deprecated="auto")

class UserRole(enum.Enum):
    PLAYER = "player"
    ADMIN = "admin"

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), nullable=True, index=True)
    role = db.Column(db.String(20), nullable=False, default=UserRole.PLAYER.value, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<User {self.email} ({self.role})>'
    
    # Role helpers
    def is_admin(self):
        return self.role == UserRole.ADMIN.value
    
    def is_player(self):
        return self.role == UserRole.PLAYER.value

class OTP(db.Model):
    __tablename__ = 'otps'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, index=True)
    code_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False, index=True)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<OTP {self.email}>'
    
    def set_code(self, code: str):
        """Hash and store the OTP code."""
        self.code_hash = otp_context.hash(code)
    
    def verify_code(self, code: str) -> bool:
        """Verify an OTP code against the stored hash."""
        return otp_context.verify(code, self.code_hash)
    
    def is_valid(self):
        """Check if OTP is still valid (not expired and not used)."""
        return not self.used and datetime.utcnow() < self.expires_at


# ============================================================================
# Enums for Market Engine
# ============================================================================

class SeasonStatus(enum.Enum):
    UPCOMING = "upcoming"
    ACTIVE = "active"
    FINISHED = "finished"


class EventStatus(enum.Enum):
    UPCOMING = "upcoming"
    LIVE = "live"
    FINISHED = "finished"


class AssetType(enum.Enum):
    PARTICIPANT = "participant"
    TEAM = "team"
    PROP = "prop"


class MarketStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    SETTLED = "settled"


class ResultStatus(enum.Enum):
    FINISHED = "finished"
    DNF = "dnf"
    DISQUALIFIED = "disqualified"


class FormulaType(enum.Enum):
    LINEAR_NORMALIZED = "linear_normalized"
    SIGMOID = "sigmoid"
    PIECEWISE = "piecewise"


class TransactionType(enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    BUY = "buy"
    SELL = "sell"
    SETTLEMENT = "settlement"
    FEE = "fee"


# ============================================================================
# Sports Ontology Models
# ============================================================================

class Sport(db.Model):
    __tablename__ = 'sports'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False, index=True)  # e.g., "F1", "NBA"
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    leagues = db.relationship('League', backref='sport', lazy=True)
    participants = db.relationship('Participant', backref='sport', lazy=True)
    teams = db.relationship('Team', backref='sport', lazy=True)
    scoring_rules = db.relationship('ScoringRule', backref='sport', lazy=True)
    
    def __repr__(self):
        return f'<Sport {self.code} ({self.name})>'


class League(db.Model):
    __tablename__ = 'leagues'
    
    id = db.Column(db.Integer, primary_key=True)
    sport_id = db.Column(db.Integer, db.ForeignKey('sports.id'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    seasons = db.relationship('Season', backref='league', lazy=True)
    
    def __repr__(self):
        return f'<League {self.name}>'


class Season(db.Model):
    __tablename__ = 'seasons'
    
    id = db.Column(db.Integer, primary_key=True)
    league_id = db.Column(db.Integer, db.ForeignKey('leagues.id'), nullable=False, index=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    status = db.Column(db.Enum(SeasonStatus), nullable=False, default=SeasonStatus.UPCOMING, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    events = db.relationship('Event', backref='season', lazy=True)
    
    def __repr__(self):
        return f'<Season {self.year} ({self.status.value})>'


class Event(db.Model):
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    season_id = db.Column(db.Integer, db.ForeignKey('seasons.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    venue = db.Column(db.String(200), nullable=True)
    start_at = db.Column(db.DateTime, nullable=True, index=True)
    end_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.Enum(EventStatus), nullable=False, default=EventStatus.UPCOMING, index=True)
    metadata_json = db.Column(db.JSON, nullable=True)  # Sport-specific info
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    markets = db.relationship('Market', backref='event', lazy=True)
    results = db.relationship('EventResult', backref='event', lazy=True)
    
    def __repr__(self):
        return f'<Event {self.name} ({self.status.value})>'


class Participant(db.Model):
    __tablename__ = 'participants'
    
    id = db.Column(db.Integer, primary_key=True)
    sport_id = db.Column(db.Integer, db.ForeignKey('sports.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    short_code = db.Column(db.String(50), nullable=True, index=True)
    metadata_json = db.Column(db.JSON, nullable=True)  # team, position, jersey number, constructor, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    assets = db.relationship('Asset', foreign_keys='Asset.participant_id', backref='participant', lazy=True)
    results = db.relationship('EventResult', backref='participant', lazy=True)
    team_memberships = db.relationship('ParticipantTeamMembership', backref='participant', lazy=True)
    
    def __repr__(self):
        return f'<Participant {self.name}>'


class Team(db.Model):
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True)
    sport_id = db.Column(db.Integer, db.ForeignKey('sports.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    short_code = db.Column(db.String(50), nullable=True, index=True)
    metadata_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    assets = db.relationship('Asset', foreign_keys='Asset.team_id', backref='team', lazy=True)
    memberships = db.relationship('ParticipantTeamMembership', backref='team', lazy=True)
    
    def __repr__(self):
        return f'<Team {self.name}>'


class ParticipantTeamMembership(db.Model):
    __tablename__ = 'participant_team_memberships'
    
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False, index=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False, index=True)
    season_id = db.Column(db.Integer, db.ForeignKey('seasons.id'), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<ParticipantTeamMembership {self.participant_id} -> {self.team_id}>'


# ============================================================================
# Asset & Market Models
# ============================================================================

class Asset(db.Model):
    __tablename__ = 'assets'
    
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(AssetType), nullable=False, index=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=True, index=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=True, index=True)
    symbol = db.Column(db.String(50), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    markets = db.relationship('Market', backref='asset', lazy=True)
    
    def __repr__(self):
        return f'<Asset {self.symbol} ({self.type.value})>'


class Market(db.Model):
    __tablename__ = 'markets'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=False, index=True)
    scoring_rule_id = db.Column(db.Integer, db.ForeignKey('scoring_rules.id'), nullable=False, index=True)
    market_type = db.Column(db.String(50), nullable=False, default='outright')
    status = db.Column(db.Enum(MarketStatus), nullable=False, default=MarketStatus.OPEN, index=True)
    a = db.Column(db.Numeric(precision=18, scale=8), nullable=False)  # Bonding curve param
    b = db.Column(db.Numeric(precision=18, scale=8), nullable=False)  # Bonding curve baseline
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    positions = db.relationship('Position', backref='market', lazy=True)
    trades = db.relationship('Trade', backref='market', lazy=True)
    price_history = db.relationship('PriceHistory', backref='market', lazy=True, order_by='PriceHistory.timestamp.desc()')
    settlement = db.relationship('MarketSettlement', backref='market', uselist=False, lazy=True)
    
    def __repr__(self):
        return f'<Market {self.id} ({self.status.value})>'


class PriceHistory(db.Model):
    __tablename__ = 'price_history'
    
    id = db.Column(db.Integer, primary_key=True)
    market_id = db.Column(db.Integer, db.ForeignKey('markets.id'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    price = db.Column(db.Numeric(precision=18, scale=8), nullable=False)
    reason = db.Column(db.String(200), nullable=True)  # e.g., "buy", "sell", "settlement"
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<PriceHistory {self.market_id} @ {self.timestamp}: {self.price}>'


class Position(db.Model):
    __tablename__ = 'positions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    market_id = db.Column(db.Integer, db.ForeignKey('markets.id'), nullable=False, index=True)
    shares = db.Column(db.Numeric(precision=18, scale=8), nullable=False, default=Decimal('0'))
    avg_entry_price = db.Column(db.Numeric(precision=18, scale=8), nullable=False, default=Decimal('0'))
    realized_pnl = db.Column(db.Numeric(precision=18, scale=8), nullable=False, default=Decimal('0'))
    last_marked_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Unique constraint: one position per user per market
    __table_args__ = (db.UniqueConstraint('user_id', 'market_id', name='uq_user_market'),)
    
    # Relationships
    user = db.relationship('User', backref='positions')
    
    def __repr__(self):
        return f'<Position user={self.user_id} market={self.market_id} shares={self.shares}>'


class Trade(db.Model):
    __tablename__ = 'trades'
    
    id = db.Column(db.Integer, primary_key=True)
    market_id = db.Column(db.Integer, db.ForeignKey('markets.id'), nullable=False, index=True)
    buyer_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    seller_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    price = db.Column(db.Numeric(precision=18, scale=8), nullable=False)
    quantity = db.Column(db.Numeric(precision=18, scale=8), nullable=False)
    executed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Relationships
    buyer = db.relationship('User', foreign_keys=[buyer_user_id], backref='buy_trades')
    seller = db.relationship('User', foreign_keys=[seller_user_id], backref='sell_trades')
    
    def __repr__(self):
        return f'<Trade {self.id} market={self.market_id} qty={self.quantity} @ {self.price}>'


# ============================================================================
# Wallet & Ledger Models
# ============================================================================

class Wallet(db.Model):
    __tablename__ = 'wallets'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False, index=True)
    balance = db.Column(db.Numeric(precision=18, scale=8), nullable=False, default=Decimal('0'))
    locked_balance = db.Column(db.Numeric(precision=18, scale=8), nullable=False, default=Decimal('0'))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='wallet', uselist=False)
    ledger_entries = db.relationship('LedgerEntry', backref='wallet', lazy=True)
    
    def __repr__(self):
        return f'<Wallet user={self.user_id} balance={self.balance} locked={self.locked_balance}>'


class LedgerEntry(db.Model):
    __tablename__ = 'ledger_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    wallet_id = db.Column(db.Integer, db.ForeignKey('wallets.id'), nullable=False, index=True)
    amount = db.Column(db.Numeric(precision=18, scale=8), nullable=False)
    transaction_type = db.Column(db.Enum(TransactionType), nullable=False, index=True)
    reference_type = db.Column(db.String(50), nullable=True)  # e.g., "market", "event"
    reference_id = db.Column(db.Integer, nullable=True, index=True)
    description = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = db.relationship('User', backref='ledger_entries')
    
    def __repr__(self):
        return f'<LedgerEntry {self.id} user={self.user_id} {self.transaction_type.value} {self.amount}>'


# ============================================================================
# Event Results & Settlement Models
# ============================================================================

class EventResult(db.Model):
    __tablename__ = 'event_results'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False, index=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participants.id'), nullable=False, index=True)
    primary_score = db.Column(db.Numeric(precision=18, scale=8), nullable=False)
    rank = db.Column(db.Integer, nullable=True, index=True)
    status = db.Column(db.Enum(ResultStatus), nullable=False, default=ResultStatus.FINISHED, index=True)
    metrics_json = db.Column(db.JSON, nullable=True)  # Additional sport-specific metrics
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Unique constraint: one result per participant per event
    __table_args__ = (db.UniqueConstraint('event_id', 'participant_id', name='uq_event_participant'),)
    
    def __repr__(self):
        return f'<EventResult event={self.event_id} participant={self.participant_id} score={self.primary_score}>'


class ScoringRule(db.Model):
    __tablename__ = 'scoring_rules'
    
    id = db.Column(db.Integer, primary_key=True)
    sport_id = db.Column(db.Integer, db.ForeignKey('sports.id'), nullable=False, index=True)
    code = db.Column(db.String(50), nullable=False, index=True)  # e.g., "F1_POINTS", "NBA_STD_FANTASY"
    max_score = db.Column(db.Numeric(precision=18, scale=8), nullable=False)
    alpha = db.Column(db.Numeric(precision=18, scale=8), nullable=False)
    beta = db.Column(db.Numeric(precision=18, scale=8), nullable=False)
    formula_type = db.Column(db.Enum(FormulaType), nullable=False, default=FormulaType.LINEAR_NORMALIZED)
    config_json = db.Column(db.JSON, nullable=True)  # Additional formula parameters
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    markets = db.relationship('Market', backref='scoring_rule', lazy=True)
    
    def __repr__(self):
        return f'<ScoringRule {self.code} (max={self.max_score})>'


class MarketSettlement(db.Model):
    __tablename__ = 'market_settlements'
    
    id = db.Column(db.Integer, primary_key=True)
    market_id = db.Column(db.Integer, db.ForeignKey('markets.id'), unique=True, nullable=False, index=True)
    settled_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    settlement_price = db.Column(db.Numeric(precision=18, scale=8), nullable=False)
    payout_per_share = db.Column(db.Numeric(precision=18, scale=8), nullable=False)
    source = db.Column(db.String(200), nullable=True)  # e.g., "event_result", "manual"
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<MarketSettlement market={self.market_id} payout={self.payout_per_share}>'

