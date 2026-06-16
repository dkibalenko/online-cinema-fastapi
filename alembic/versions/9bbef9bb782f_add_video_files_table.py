"""add video_files table

Revision ID: 9bbef9bb782f
Revises: d3f8a1c2e9b4
Create Date: 2026-06-14 11:17:03.145354

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9bbef9bb782f'
down_revision: Union[str, Sequence[str], None] = 'd3f8a1c2e9b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "video_files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "processing",
                "ready",
                "failed",
                name="videostatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("raw_key", sa.String(length=500), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["movie_id"], ["movies.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"], ["users.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_video_files_movie_id"),
        "video_files",
        ["movie_id"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_video_files_movie_id"), table_name="video_files")
    op.drop_table("video_files")
    sa.Enum(name="videostatus").drop(op.get_bind(), checkfirst=True)
