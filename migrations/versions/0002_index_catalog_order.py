"""index the catalog order (title, id)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Listing and export are ordered by (title, id); without this index every page
    # request and the start of every export sorts the whole table.
    op.create_index("ix_podcasts_title_id", "podcasts", ["title", "id"])


def downgrade() -> None:
    op.drop_index("ix_podcasts_title_id", table_name="podcasts")
