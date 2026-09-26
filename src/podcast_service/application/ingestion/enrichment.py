import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, replace

from podcast_service.domain.ingestion.normalizer import PodcastNormalizer
from podcast_service.domain.ingestion.ports import FeedReader, ImageFetcher, PaletteExtractor
from podcast_service.domain.podcast.entities import Podcast
from podcast_service.domain.podcast.value_objects import ColorPalette


@dataclass(frozen=True, slots=True)
class EnrichmentResult:
    podcast: Podcast
    palette_failed: bool  # it has a cover, but no palette could be produced


class PodcastEnricher:
    """Adds RSS details and the cover color palette to normalized podcasts.

    Every step is best effort: a broken feed or cover leaves the podcast as it was,
    and the failure is reported instead of raised.
    """

    def __init__(
        self,
        feed_reader: FeedReader,
        image_fetcher: ImageFetcher,
        palette_extractor: PaletteExtractor,
        normalizer: PodcastNormalizer,
        max_concurrency: int,
    ) -> None:
        self._feed_reader = feed_reader
        self._image_fetcher = image_fetcher
        self._palette_extractor = palette_extractor
        self._normalizer = normalizer
        self._max_concurrency = max_concurrency

    async def enrich_many(self, podcasts: Sequence[Podcast]) -> list[EnrichmentResult]:
        """Enrich concurrently (bounded, to be polite to upstream hosts), keeping order."""
        semaphore = asyncio.Semaphore(self._max_concurrency)

        async def bounded(podcast: Podcast) -> EnrichmentResult:
            async with semaphore:
                return await self.enrich(podcast)

        return list(await asyncio.gather(*(bounded(podcast) for podcast in podcasts)))

    async def enrich(self, podcast: Podcast) -> EnrichmentResult:
        enriched, palette = await asyncio.gather(
            self._with_feed_details(podcast), self._palette(podcast.cover_image_url)
        )
        return EnrichmentResult(
            podcast=replace(enriched, palette=palette),
            palette_failed=podcast.cover_image_url is not None and palette is None,
        )

    async def _with_feed_details(self, podcast: Podcast) -> Podcast:
        if podcast.feed_url is None:
            return podcast
        details = await self._feed_reader.read(podcast.feed_url)
        if details is None:
            return podcast
        return self._normalizer.apply_feed_details(podcast, details)

    async def _palette(self, cover_url: str | None) -> ColorPalette | None:
        if cover_url is None:
            return None
        image = await self._image_fetcher.fetch(cover_url)
        if image is None:
            return None
        # Decoding and quantizing is CPU-bound; keep it off the event loop.
        return await asyncio.to_thread(self._palette_extractor.extract, image)
