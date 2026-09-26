"""In-memory fakes of the ingestion ports, shared by application-layer tests."""

import asyncio

from podcast_service.domain.ingestion.ports import (
    FeedDetails,
    FeedReader,
    ImageFetcher,
    PaletteExtractor,
)
from podcast_service.domain.podcast.value_objects import ColorPalette

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
