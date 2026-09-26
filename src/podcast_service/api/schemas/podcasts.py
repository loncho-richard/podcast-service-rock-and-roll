from datetime import datetime
from math import ceil
from uuid import UUID

from pydantic import BaseModel, Field

from podcast_service.domain.podcast.entities import Podcast
from podcast_service.domain.podcast.filters import Page


class PodcastResponse(BaseModel):
    id: UUID
    source: str = Field(examples=["itunes"])
    external_id: str = Field(
        description="Id of the podcast in its source.", examples=["1618650164"]
    )
    title: str
    author: str
    description: str | None
    language: str | None = Field(examples=["en-US"])
    country: str | None
    genres: list[str] = Field(examples=[["Music History", "Music"]])
    primary_genre: str | None
    feed_url: str | None
    store_url: str | None
    cover_image_url: str | None
    palette: list[str] | None = Field(
        description="Dominant cover colors as hex, most dominant first; null if unavailable.",
        examples=[["#1a1a1a", "#c0392b", "#f5f5f5"]],
    )
    explicit: bool
    episode_count: int | None
    released_at: datetime | None = Field(description="Date of the latest episode.")
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, podcast: Podcast) -> "PodcastResponse":
        if podcast.id is None or podcast.created_at is None or podcast.updated_at is None:
            raise ValueError("Only stored podcasts can be serialized.")
        return cls(
            id=podcast.id,
            source=podcast.ref.source,
            external_id=podcast.ref.external_id,
            title=podcast.title,
            author=podcast.author,
            description=podcast.description,
            language=podcast.language,
            country=podcast.country,
            genres=list(podcast.genres),
            primary_genre=podcast.primary_genre,
            feed_url=podcast.feed_url,
            store_url=podcast.store_url,
            cover_image_url=podcast.cover_image_url,
            palette=podcast.palette.to_hex() if podcast.palette else None,
            explicit=podcast.explicit,
            episode_count=podcast.episode_count,
            released_at=podcast.released_at,
            created_at=podcast.created_at,
            updated_at=podcast.updated_at,
        )


class PodcastPage(BaseModel):
    items: list[PodcastResponse]
    page: int
    page_size: int
    total: int = Field(description="Podcasts matching the filters, across all pages.")
    total_pages: int

    @classmethod
    def from_domain(cls, page: Page[Podcast]) -> "PodcastPage":
        return cls(
            items=[PodcastResponse.from_domain(podcast) for podcast in page.items],
            page=page.page,
            page_size=page.page_size,
            total=page.total,
            total_pages=ceil(page.total / page.page_size),
        )
