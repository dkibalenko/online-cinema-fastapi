"""Add updated_at trigger for movie_comments

Revision ID: c7d9e2f4a1b3
Revises: baebaa901225
Create Date: 2026-06-05 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "c7d9e2f4a1b3"
down_revision: str | Sequence[str] | None = "baebaa901225"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_movie_comments_updated_at
        BEFORE UPDATE ON movie_comments
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_movie_comments_updated_at ON movie_comments;"
    )
    op.execute("DROP FUNCTION IF EXISTS set_updated_at;")
