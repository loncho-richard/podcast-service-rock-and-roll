from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PodcastModel(Base):
    __tablename__ = "podcasts"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_podcasts_source_external_id"),
        # Trigram indexes back the case-insensitive substring search on title/author.
        Index(
            "ix_podcasts_title_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"},
        ),
        Index(
            "ix_podcasts_author_trgm",
            "author",
            postgresql_using="gin",
            postgresql_ops={"author": "gin_trgm_ops"},
        ),
        Index("ix_podcasts_genres", "genres", postgresql_using="gin"),
        Index("ix_podcasts_language", "language"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(Text)
    author: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(35))
    country: Mapped[str | None] = mapped_column(String(64))
    genres: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    primary_genre: Mapped[str | None] = mapped_column(Text)
    feed_url: Mapped[str | None] = mapped_column(Text)
    store_url: Mapped[str | None] = mapped_column(Text)
    cover_image_url: Mapped[str | None] = mapped_column(Text)
    palette: Mapped[list[Any] | None] = mapped_column(JSONB)
    explicit: Mapped[bool] = mapped_column(server_default="false")
    episode_count: Mapped[int | None]
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
