"""Increase market duration default from 10s to 60s

Revision ID: h5c6d7e8f9a0
Revises: g4b5c6d7e8f9
Create Date: 2026-02-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'h5c6d7e8f9a0'
down_revision = 'g4b5c6d7e8f9'
branch_labels = None
depends_on = None


def upgrade():
    # Update the server default
    op.alter_column('replay_sessions', 'market_duration_seconds',
                    server_default='60')
    # Update existing sessions that still have the old default
    op.execute("UPDATE replay_sessions SET market_duration_seconds = 60 WHERE market_duration_seconds = 10")


def downgrade():
    op.alter_column('replay_sessions', 'market_duration_seconds',
                    server_default='10')
    op.execute("UPDATE replay_sessions SET market_duration_seconds = 10 WHERE market_duration_seconds = 60")
