import pytest

from fakes import FEED_URL, FakeFeedReader, FakeImageFetcher, FakePaletteExtractor
from podcast_service.application.ingestion.enrichment import PodcastEnricher
from podcast_service.domain.ingestion.normalizer import PodcastNormalizer
from podcast_service.domain.ingestion.ports import FeedDetails
from podcast_service.domain.ingestion.relevance import RockRelevancePolicy


@pytest.fixture
def feed_reader() -> FakeFeedReader:
    return FakeFeedReader(
        {FEED_URL: FeedDetails(description="<p>From the <b>feed</b></p>", language="en-gb")}
    )


@pytest.fixture
def enricher(feed_reader: FakeFeedReader) -> PodcastEnricher:
    return PodcastEnricher(
        feed_reader=feed_reader,
        image_fetcher=FakeImageFetcher(),
        palette_extractor=FakePaletteExtractor(),
        normalizer=PodcastNormalizer(RockRelevancePolicy()),
        max_concurrency=3,
    )
