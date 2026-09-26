"""Outbound ports of the ingestion context, implemented in the infrastructure layer.

Enrichment ports return None instead of raising: a missing feed or a broken cover
image must never fail an ingestion.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from podcast_service.domain.ingestion.raw import RawPodcastRecord
from podcast_service.domain.ingestion.summary import SourceMode
from podcast_service.domain.podcast import ColorPalette


@dataclass(frozen=True, slots=True)
class SourceBatch:
    records: list[RawPodcastRecord]
    mode: SourceMode


@dataclass(frozen=True, slots=True)
class FeedDetails:
    description: str | None = None
    language: str | None = None


class PodcastSource(ABC):
    @abstractmethod
    async def search(self, terms: Sequence[str], limit: int) -> SourceBatch: ...

    @abstractmethod
    async def lookup(self, external_id: str) -> RawPodcastRecord | None: ...


class FeedReader(ABC):
    @abstractmethod
    async def read(self, feed_url: str) -> FeedDetails | None: ...


class ImageFetcher(ABC):
    @abstractmethod
    async def fetch(self, url: str) -> bytes | None: ...


class PaletteExtractor(ABC):
    @abstractmethod
    def extract(self, image: bytes) -> ColorPalette | None: ...
