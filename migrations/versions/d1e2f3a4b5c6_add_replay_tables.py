"""Add replay tables for Replay 2024 Season feature

Revision ID: d1e2f3a4b5c6
Revises: c1a2b3d4e5f6
Create Date: 2025-12-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1e2f3a4b5c6'
down_revision = 'c1a2b3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Create replay_sessions table
    op.create_table('replay_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('current_race', sa.Integer(), nullable=False, default=0),
        sa.Column('status', sa.Enum('ACTIVE', 'COMPLETED', 'ABANDONED', name='replaysessionstatus'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('final_balance', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('replay_sessions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_replay_sessions_user_id'), ['user_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_replay_sessions_status'), ['status'], unique=False)

    # Create replay_wallets table
    op.create_table('replay_wallets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('balance', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('locked_balance', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['replay_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('replay_wallets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_replay_wallets_session_id'), ['session_id'], unique=True)

    # Create replay_markets table
    op.create_table('replay_markets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('race_number', sa.Integer(), nullable=False),
        sa.Column('driver_code', sa.String(length=10), nullable=False),
        sa.Column('driver_name', sa.String(length=100), nullable=False),
        sa.Column('team_name', sa.String(length=100), nullable=True),
        sa.Column('status', sa.Enum('OPEN', 'CLOSED', 'SETTLED', name='marketstatus'), nullable=False),
        sa.Column('a', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('b', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('settlement_price', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column('payout_per_share', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['replay_sessions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'race_number', 'driver_code', name='uq_replay_market')
    )
    with op.batch_alter_table('replay_markets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_replay_markets_session_id'), ['session_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_replay_markets_race_number'), ['race_number'], unique=False)
        batch_op.create_index(batch_op.f('ix_replay_markets_driver_code'), ['driver_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_replay_markets_status'), ['status'], unique=False)

    # Create replay_positions table
    op.create_table('replay_positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('market_id', sa.Integer(), nullable=False),
        sa.Column('shares', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('avg_entry_price', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('realized_pnl', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['market_id'], ['replay_markets.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['replay_sessions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'market_id', name='uq_replay_position')
    )
    with op.batch_alter_table('replay_positions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_replay_positions_session_id'), ['session_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_replay_positions_market_id'), ['market_id'], unique=False)

    # Create replay_trades table
    op.create_table('replay_trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('market_id', sa.Integer(), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('price', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('cost_or_payout', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['market_id'], ['replay_markets.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['replay_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('replay_trades', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_replay_trades_session_id'), ['session_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_replay_trades_market_id'), ['market_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_replay_trades_executed_at'), ['executed_at'], unique=False)

    # Create replay_ledger_entries table
    op.create_table('replay_ledger_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('transaction_type', sa.Enum('DEPOSIT', 'WITHDRAWAL', 'BUY', 'SELL', 'SETTLEMENT', 'FEE', name='transactiontype'), nullable=False),
        sa.Column('reference_type', sa.String(length=50), nullable=True),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['replay_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('replay_ledger_entries', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_replay_ledger_entries_session_id'), ['session_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_replay_ledger_entries_transaction_type'), ['transaction_type'], unique=False)
        batch_op.create_index(batch_op.f('ix_replay_ledger_entries_created_at'), ['created_at'], unique=False)

    # Create replay_price_history table
    op.create_table('replay_price_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('market_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('price', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('supply', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('reason', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['market_id'], ['replay_markets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('replay_price_history', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_replay_price_history_market_id'), ['market_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_replay_price_history_timestamp'), ['timestamp'], unique=False)


def downgrade():
    # Drop tables in reverse order
    op.drop_table('replay_price_history')
    op.drop_table('replay_ledger_entries')
    op.drop_table('replay_trades')
    op.drop_table('replay_positions')
    op.drop_table('replay_markets')
    op.drop_table('replay_wallets')
    op.drop_table('replay_sessions')

    # Drop enum type (only if not used elsewhere)
    op.execute('DROP TYPE IF EXISTS replaysessionstatus')
