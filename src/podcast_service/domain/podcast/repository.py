from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from enum import StrEnum
from uuid import UUID

from podcast_service.domain.podcast.entities import Podcast
from podcast_service.domain.podcast.filters import Page, PageRequest, PodcastFilters


class UpsertOutcome(StrEnum):
    CREATED = "created"
    UPDATED = "updated"


class PodcastRepository(ABC):
    @abstractmethod
    async def upsert(self, podcast: Podcast) -> tuple[Podcast, UpsertOutcome]:
        """Insert or update by `ref` (source + external id). Returns the stored podcast."""

    @abstractmethod
    async def get(self, podcast_id: UUID) -> Podcast | None: ...

    @abstractmethod
    async def list(self, filters: PodcastFilters, page: PageRequest) -> Page[Podcast]: ...

    @abstractmethod
    def stream_all(self) -> AsyncIterator[Podcast]:
        """Yield every podcast without loading the whole catalog in memory."""
