"""Add difficulty levels and driver positions for Replay feature

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2025-12-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2f3a4b5c6d7'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade():
    # Create difficulty enum type
    op.execute("CREATE TYPE replaydifficulty AS ENUM ('easy', 'medium', 'hard')")

    # Add difficulty column to replay_sessions
    op.add_column('replay_sessions',
        sa.Column('difficulty', sa.Enum('easy', 'medium', 'hard', name='replaydifficulty'),
                  nullable=False, server_default='medium'))
    op.create_index('ix_replay_sessions_difficulty', 'replay_sessions', ['difficulty'])

    # Create replay_ai_players table for AI competition
    op.create_table('replay_ai_players',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('difficulty', sa.Enum('easy', 'medium', 'hard', name='replaydifficulty'), nullable=False),
        sa.Column('final_balance', sa.Numeric(precision=18, scale=8), nullable=False),
        sa.Column('strategy_type', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_replay_ai_players_difficulty', 'replay_ai_players', ['difficulty'])

    # Create replay_driver_positions table for carry-forward positions
    op.create_table('replay_driver_positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('driver_code', sa.String(length=10), nullable=False),
        sa.Column('shares', sa.Numeric(precision=18, scale=8), nullable=False, server_default='0'),
        sa.Column('total_cost_basis', sa.Numeric(precision=18, scale=8), nullable=False, server_default='0'),
        sa.Column('cumulative_payouts', sa.Numeric(precision=18, scale=8), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['session_id'], ['replay_sessions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'driver_code', name='uq_replay_driver_position')
    )
    op.create_index('ix_replay_driver_positions_session_id', 'replay_driver_positions', ['session_id'])
    op.create_index('ix_replay_driver_positions_driver_code', 'replay_driver_positions', ['driver_code'])


def downgrade():
    # Drop tables
    op.drop_table('replay_driver_positions')
    op.drop_table('replay_ai_players')

    # Drop difficulty column
    op.drop_index('ix_replay_sessions_difficulty', table_name='replay_sessions')
    op.drop_column('replay_sessions', 'difficulty')

    # Drop enum type
    op.execute('DROP TYPE IF EXISTS replaydifficulty')
