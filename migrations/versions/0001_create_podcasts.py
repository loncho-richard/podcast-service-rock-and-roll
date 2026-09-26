"""create podcasts table

Revision ID: 0001
Revises:
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "podcasts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("language", sa.String(35), nullable=True),
        sa.Column("country", sa.String(64), nullable=True),
        sa.Column("genres", postgresql.ARRAY(sa.Text()), server_default="{}", nullable=False),
        sa.Column("primary_genre", sa.Text(), nullable=True),
        sa.Column("feed_url", sa.Text(), nullable=True),
        sa.Column("store_url", sa.Text(), nullable=True),
        sa.Column("cover_image_url", sa.Text(), nullable=True),
        sa.Column("palette", postgresql.JSONB(), nullable=True),
        sa.Column("explicit", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("episode_count", sa.Integer(), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("source", "external_id", name="uq_podcasts_source_external_id"),
    )
    op.create_index(
        "ix_podcasts_title_trgm",
        "podcasts",
        ["title"],
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_podcasts_author_trgm",
        "podcasts",
        ["author"],
        postgresql_using="gin",
        postgresql_ops={"author": "gin_trgm_ops"},
    )
    op.create_index("ix_podcasts_genres", "podcasts", ["genres"], postgresql_using="gin")
    op.create_index("ix_podcasts_language", "podcasts", ["language"])


def downgrade() -> None:
    op.drop_table("podcasts")
