"""Add timer-based replay columns and scheduled AI trades table

Revision ID: g4b5c6d7e8f9
Revises: f3a4b5c6d7e8
Create Date: 2026-01-23 23:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g4b5c6d7e8f9'
down_revision = 'f3a4b5c6d7e8'
branch_labels = None
depends_on = None


def upgrade():
    # Add timer columns to replay_sessions
    op.add_column('replay_sessions', sa.Column('market_opens_at', sa.DateTime(), nullable=True))
    op.add_column('replay_sessions', sa.Column('market_duration_seconds', sa.Integer(), nullable=False, server_default='30'))

    # Create replay_scheduled_ai_trades table
    op.create_table('replay_scheduled_ai_trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('market_id', sa.Integer(), nullable=False),
        sa.Column('ai_player_name', sa.String(length=100), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('execution_price', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column('execution_cost', sa.Numeric(precision=18, scale=8), nullable=True),
        sa.ForeignKeyConstraint(['market_id'], ['replay_markets.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['replay_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_replay_scheduled_ai_trades_market_id'), 'replay_scheduled_ai_trades', ['market_id'], unique=False)
    op.create_index(op.f('ix_replay_scheduled_ai_trades_scheduled_at'), 'replay_scheduled_ai_trades', ['scheduled_at'], unique=False)
    op.create_index(op.f('ix_replay_scheduled_ai_trades_session_id'), 'replay_scheduled_ai_trades', ['session_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_replay_scheduled_ai_trades_session_id'), table_name='replay_scheduled_ai_trades')
    op.drop_index(op.f('ix_replay_scheduled_ai_trades_scheduled_at'), table_name='replay_scheduled_ai_trades')
    op.drop_index(op.f('ix_replay_scheduled_ai_trades_market_id'), table_name='replay_scheduled_ai_trades')
    op.drop_table('replay_scheduled_ai_trades')
    op.drop_column('replay_sessions', 'market_duration_seconds')
    op.drop_column('replay_sessions', 'market_opens_at')
