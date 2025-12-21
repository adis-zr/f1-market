"""Fix replaydifficulty enum case to match SQLAlchemy expectations

The migration e2f3a4b5c6d7 created the replaydifficulty enum with lowercase values
('easy', 'medium', 'hard'), but SQLAlchemy's db.Enum(ReplayDifficulty) expects
uppercase values ('EASY', 'MEDIUM', 'HARD') - it uses Python enum names, not values.

This migration fixes the enum values to be uppercase.

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2025-12-20

"""
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'f3a4b5c6d7e8'
down_revision = 'e2f3a4b5c6d7'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Check if the enum exists and what values it has
    result = conn.execute(text("""
        SELECT enumlabel FROM pg_enum
        JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
        WHERE pg_type.typname = 'replaydifficulty'
        ORDER BY enumsortorder
    """))
    current_values = [row[0] for row in result]

    # If already uppercase, nothing to do
    if current_values and current_values[0] == 'EASY':
        return

    # If empty (enum doesn't exist), create it with correct values
    if not current_values:
        conn.execute(text("""
            CREATE TYPE replaydifficulty AS ENUM ('EASY', 'MEDIUM', 'HARD')
        """))
        return

    # If lowercase, we need to fix it
    if current_values and current_values[0] == 'easy':
        # Step 1: Create a new enum type with uppercase values
        conn.execute(text("""
            CREATE TYPE replaydifficulty_new AS ENUM ('EASY', 'MEDIUM', 'HARD')
        """))

        # Step 2: Drop the default on replay_sessions.difficulty (it references the old enum)
        conn.execute(text("""
            ALTER TABLE replay_sessions
            ALTER COLUMN difficulty DROP DEFAULT
        """))

        # Step 3: Update replay_sessions.difficulty column type
        conn.execute(text("""
            ALTER TABLE replay_sessions
            ALTER COLUMN difficulty TYPE replaydifficulty_new
            USING (
                CASE difficulty::text
                    WHEN 'easy' THEN 'EASY'::replaydifficulty_new
                    WHEN 'medium' THEN 'MEDIUM'::replaydifficulty_new
                    WHEN 'hard' THEN 'HARD'::replaydifficulty_new
                    ELSE difficulty::text::replaydifficulty_new
                END
            )
        """))

        # Step 4: Update replay_ai_players.difficulty column
        conn.execute(text("""
            ALTER TABLE replay_ai_players
            ALTER COLUMN difficulty TYPE replaydifficulty_new
            USING (
                CASE difficulty::text
                    WHEN 'easy' THEN 'EASY'::replaydifficulty_new
                    WHEN 'medium' THEN 'MEDIUM'::replaydifficulty_new
                    WHEN 'hard' THEN 'HARD'::replaydifficulty_new
                    ELSE difficulty::text::replaydifficulty_new
                END
            )
        """))

        # Step 5: Drop the old type and rename the new one
        conn.execute(text("DROP TYPE replaydifficulty"))
        conn.execute(text("ALTER TYPE replaydifficulty_new RENAME TO replaydifficulty"))

        # Step 6: Re-add the default with uppercase value
        conn.execute(text("""
            ALTER TABLE replay_sessions
            ALTER COLUMN difficulty SET DEFAULT 'MEDIUM'::replaydifficulty
        """))


def downgrade():
    conn = op.get_bind()

    # Check current values
    result = conn.execute(text("""
        SELECT enumlabel FROM pg_enum
        JOIN pg_type ON pg_enum.enumtypid = pg_type.oid
        WHERE pg_type.typname = 'replaydifficulty'
        ORDER BY enumsortorder
    """))
    current_values = [row[0] for row in result]

    # If already lowercase, nothing to do
    if not current_values or current_values[0] == 'easy':
        return

    # Reverse: convert uppercase back to lowercase
    conn.execute(text("""
        CREATE TYPE replaydifficulty_new AS ENUM ('easy', 'medium', 'hard')
    """))

    # Drop the default first
    conn.execute(text("""
        ALTER TABLE replay_sessions
        ALTER COLUMN difficulty DROP DEFAULT
    """))

    conn.execute(text("""
        ALTER TABLE replay_sessions
        ALTER COLUMN difficulty TYPE replaydifficulty_new
        USING (
            CASE difficulty::text
                WHEN 'EASY' THEN 'easy'::replaydifficulty_new
                WHEN 'MEDIUM' THEN 'medium'::replaydifficulty_new
                WHEN 'HARD' THEN 'hard'::replaydifficulty_new
                ELSE difficulty::text::replaydifficulty_new
            END
        )
    """))

    conn.execute(text("""
        ALTER TABLE replay_ai_players
        ALTER COLUMN difficulty TYPE replaydifficulty_new
        USING (
            CASE difficulty::text
                WHEN 'EASY' THEN 'easy'::replaydifficulty_new
                WHEN 'MEDIUM' THEN 'medium'::replaydifficulty_new
                WHEN 'HARD' THEN 'hard'::replaydifficulty_new
                ELSE difficulty::text::replaydifficulty_new
            END
        )
    """))

    conn.execute(text("DROP TYPE replaydifficulty"))
    conn.execute(text("ALTER TYPE replaydifficulty_new RENAME TO replaydifficulty"))

    # Re-add the default with lowercase value
    conn.execute(text("""
        ALTER TABLE replay_sessions
        ALTER COLUMN difficulty SET DEFAULT 'medium'::replaydifficulty
    """))
