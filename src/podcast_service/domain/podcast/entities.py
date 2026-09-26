from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from podcast_service.domain.podcast.value_objects import ColorPalette, ExternalRef


@dataclass(slots=True, kw_only=True)
class Podcast:
    """Aggregate root of the catalog. `id` is assigned when the podcast is first stored."""

    ref: ExternalRef
    title: str
    author: str
    description: str | None = None
    language: str | None = None
    country: str | None = None
    genres: tuple[str, ...] = ()
    primary_genre: str | None = None
    feed_url: str | None = None
    store_url: str | None = None
    cover_image_url: str | None = None
    palette: ColorPalette | None = None
    explicit: bool = False
    episode_count: int | None = None
    released_at: datetime | None = None
    id: UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
