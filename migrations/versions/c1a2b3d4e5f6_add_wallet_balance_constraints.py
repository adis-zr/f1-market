"""add_wallet_balance_constraints

Revision ID: c1a2b3d4e5f6
Revises: b50457341350
Create Date: 2025-12-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1a2b3d4e5f6'
down_revision = 'b50457341350'
branch_labels = None
depends_on = None


def upgrade():
    """Add CHECK constraints to ensure wallet balances cannot go negative."""
    # Add CHECK constraint for balance >= 0
    op.create_check_constraint(
        'ck_wallet_balance_non_negative',
        'wallets',
        sa.column('balance') >= 0
    )

    # Add CHECK constraint for locked_balance >= 0
    op.create_check_constraint(
        'ck_wallet_locked_balance_non_negative',
        'wallets',
        sa.column('locked_balance') >= 0
    )


def downgrade():
    """Remove CHECK constraints."""
    op.drop_constraint('ck_wallet_locked_balance_non_negative', 'wallets', type_='check')
    op.drop_constraint('ck_wallet_balance_non_negative', 'wallets', type_='check')
