"""make_buyer_user_id_nullable

Revision ID: b50457341350
Revises: 8f617b4b5aed
Create Date: 2025-12-17 19:09:03.277893

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b50457341350'
down_revision = '8f617b4b5aed'
branch_labels = None
depends_on = None


def upgrade():
    # Make buyer_user_id nullable to support AMM sell trades where there's no buyer
    with op.batch_alter_table('trades', schema=None) as batch_op:
        batch_op.alter_column('buyer_user_id',
                              existing_type=sa.Integer(),
                              nullable=True)


def downgrade():
    # Revert to NOT NULL (will fail if NULL values exist)
    with op.batch_alter_table('trades', schema=None) as batch_op:
        batch_op.alter_column('buyer_user_id',
                              existing_type=sa.Integer(),
                              nullable=False)
