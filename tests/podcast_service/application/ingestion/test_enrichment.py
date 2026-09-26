from dataclasses import replace
from typing import Any

import pytest

from factories import PodcastFactory
from fakes import (
    BROKEN_COVER_URL,
    COVER_PALETTE,
    COVER_URL,
    CRASHING_COVER_URL,
    FEED_URL,
    UNDECODABLE_COVER_URL,
    FakeFeedReader,
)
from podcast_service.application.ingestion.enrichment import EnrichmentResult, PodcastEnricher


async def test_feed_details_and_palette_are_added(enricher: PodcastEnricher) -> None:
    podcast = PodcastFactory.build(feed_url=FEED_URL, cover_image_url=COVER_URL, palette=None)

    result = await enricher.enrich(podcast)

    assert result == EnrichmentResult(
        podcast=replace(
            podcast, description="From the feed", language="en-GB", palette=COVER_PALETTE
        ),
        palette_failed=False,
    )


@pytest.mark.parametrize(
    ("overrides", "palette_failed"),
    [
        ({"cover_image_url": None}, False),
        ({"cover_image_url": BROKEN_COVER_URL}, True),
        ({"cover_image_url": UNDECODABLE_COVER_URL}, True),
        ({"cover_image_url": CRASHING_COVER_URL}, True),
    ],
    ids=["no-cover", "download-fails", "extraction-fails", "extractor-crashes"],
)
async def test_missing_or_broken_covers_never_fail_the_podcast(
    enricher: PodcastEnricher, overrides: dict[str, Any], palette_failed: bool
) -> None:
    podcast = PodcastFactory.build(feed_url=None, palette=None, **overrides)

    result = await enricher.enrich(podcast)

    assert result == EnrichmentResult(podcast=podcast, palette_failed=palette_failed)


@pytest.mark.parametrize(
    "feed_url",
    [None, "https://feeds.example.com/unreachable.xml"],
    ids=["no-feed", "unreadable-feed"],
)
async def test_without_a_usable_feed_the_podcast_keeps_its_details(
    enricher: PodcastEnricher, feed_url: str | None
) -> None:
    podcast = PodcastFactory.build(feed_url=feed_url, cover_image_url=None, palette=None)

    result = await enricher.enrich(podcast)

    assert result.podcast == podcast


async def test_enrich_many_keeps_order_and_bounds_concurrency(
    enricher: PodcastEnricher, feed_reader: FakeFeedReader
) -> None:
    podcasts = PodcastFactory.batch(10, feed_url=FEED_URL, cover_image_url=None)

    results = await enricher.enrich_many(podcasts)

    assert ([r.podcast.ref for r in results], feed_reader.peak_concurrency) == (
        [p.ref for p in podcasts],
        3,
    )
