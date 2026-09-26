"""In-memory fakes of the ports, shared by application and API tests."""

import asyncio
from collections.abc import AsyncIterator, Iterable, Sequence
from dataclasses import replace
from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID, uuid4

from factories import RawPodcastRecordFactory
from podcast_service.application.unit_of_work import UnitOfWork
from podcast_service.domain.ingestion.errors import SourceUnavailableError
from podcast_service.domain.ingestion.ports import (
    FeedDetails,
    FeedReader,
    ImageFetcher,
    PaletteExtractor,
    PodcastSource,
    SourceBatch,
)
from podcast_service.domain.ingestion.raw import RawPodcastRecord
from podcast_service.domain.ingestion.summary import SourceMode
from podcast_service.domain.podcast.entities import Podcast
from podcast_service.domain.podcast.filters import Page, PageRequest, PodcastFilters
from podcast_service.domain.podcast.repository import PodcastRepository, UpsertOutcome
from podcast_service.domain.podcast.value_objects import ColorPalette, ExternalRef

FEED_URL = "https://feeds.example.com/classic-rock.xml"
COVER_URL = "https://images.example.com/classic-rock.jpg"
BROKEN_COVER_URL = "https://images.example.com/broken.jpg"
UNDECODABLE_COVER_URL = "https://images.example.com/undecodable.jpg"
COVER_PALETTE = ColorPalette.from_hex(["#111111", "#eeeeee"])


class FakeFeedReader(FeedReader):
    """Serves known feeds and records the peak number of concurrent reads."""

    def __init__(self, feeds: dict[str, FeedDetails]) -> None:
        self._feeds = feeds
        self._in_flight = 0
        self.peak_concurrency = 0

    async def read(self, feed_url: str) -> FeedDetails | None:
        self._in_flight += 1
        self.peak_concurrency = max(self.peak_concurrency, self._in_flight)
        await asyncio.sleep(0.01)
        self._in_flight -= 1
        return self._feeds.get(feed_url)


class FakeImageFetcher(ImageFetcher):
    """COVER_URL is a good image, UNDECODABLE_COVER_URL downloads but is corrupt,
    anything else fails to download."""

    async def fetch(self, url: str) -> bytes | None:
        return {COVER_URL: b"good-image", UNDECODABLE_COVER_URL: b"corrupt"}.get(url)


class FakePaletteExtractor(PaletteExtractor):
    def extract(self, image: bytes) -> ColorPalette | None:
        return COVER_PALETTE if image == b"good-image" else None


# --- source -------------------------------------------------------------------

UNAVAILABLE_ID = "5000"  # lookups of this id behave as if the source were down


def upstream_records() -> list[RawPodcastRecord]:
    """What the source returns: two good podcasts plus every kind of bad record."""
    return [
        RawPodcastRecordFactory.build(
            external_id="1001", title="Classic Rock Hour", feed_url=FEED_URL, artwork_url=COVER_URL
        ),
        RawPodcastRecordFactory.build(
            external_id="1002",
            title="Punk Tapes",
            author="Garage Collective",
            feed_url=None,
            artwork_url=BROKEN_COVER_URL,
        ),
        RawPodcastRecordFactory.build(
            external_id="1003", title="Jazz Standards", author="Blue Note Radio"
        ),
        RawPodcastRecordFactory.build(external_id="1004", title="<p></p>"),
        RawPodcastRecordFactory.build(external_id="1001", title="Classic Rock Hour (mirror)"),
    ]


class FakePodcastSource(PodcastSource):
    def __init__(
        self, records: Sequence[RawPodcastRecord], mode: SourceMode = SourceMode.LIVE
    ) -> None:
        self._records = list(records)
        self._mode = mode
        self.searched_terms: list[str] = []

    async def search(self, terms: Sequence[str], limit: int) -> SourceBatch:
        self.searched_terms = list(terms)
        return SourceBatch(self._records[:limit], self._mode)

    async def lookup(self, external_id: str) -> RawPodcastRecord | None:
        if external_id == UNAVAILABLE_ID:
            raise SourceUnavailableError("The podcast source is unavailable.")
        return next((r for r in self._records if r.external_id == external_id), None)


# --- persistence ----------------------------------------------------------------


class InMemoryPodcastRepository(PodcastRepository):
    def __init__(self) -> None:
        self.podcasts: dict[ExternalRef, Podcast] = {}

    async def upsert(self, podcast: Podcast) -> tuple[Podcast, UpsertOutcome]:
        now = datetime.now(UTC)
        current = self.podcasts.get(podcast.ref)
        if current is None:
            stored = replace(podcast, id=uuid4(), created_at=now, updated_at=now)
            outcome = UpsertOutcome.CREATED
        elif replace(current, id=None, created_at=None, updated_at=None) == podcast:
            return current, UpsertOutcome.UNCHANGED
        else:
            stored = replace(podcast, id=current.id, created_at=current.created_at, updated_at=now)
            outcome = UpsertOutcome.UPDATED
        self.podcasts[podcast.ref] = stored
        return stored, outcome

    async def get(self, podcast_id: UUID) -> Podcast | None:
        return next((p for p in self.podcasts.values() if p.id == podcast_id), None)

    async def list(self, filters: PodcastFilters, page: PageRequest) -> Page[Podcast]:
        items = sorted(self.podcasts.values(), key=lambda p: p.title)
        window = items[page.offset : page.offset + page.page_size]
        return Page(items=window, total=len(items), page=page.page, page_size=page.page_size)

    async def stream_all(self) -> AsyncIterator[Podcast]:
        for podcast in sorted(self.podcasts.values(), key=lambda p: p.title):
            yield podcast


class InMemoryUnitOfWork(UnitOfWork):
    """Shares one repository across units of work; counts commits and closed units."""

    def __init__(self, repository: InMemoryPodcastRepository) -> None:
        self.podcasts = repository
        self.commits = 0
        self.exits = 0

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.exits += 1

    async def commit(self) -> None:
        self.commits += 1


async def as_stream(podcasts: Iterable[Podcast]) -> AsyncIterator[Podcast]:
    """Present a plain list the way `PodcastRepository.stream_all` yields rows."""
    for podcast in podcasts:
        yield podcast
