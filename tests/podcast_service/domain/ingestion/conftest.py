from datetime import UTC, datetime

import pytest

from factories import RawPodcastRecordFactory
from podcast_service.domain.ingestion.normalizer import PodcastNormalizer
from podcast_service.domain.ingestion.raw import RawPodcastRecord
from podcast_service.domain.ingestion.relevance import RockRelevancePolicy
from podcast_service.domain.podcast.entities import Podcast
from podcast_service.domain.podcast.value_objects import ExternalRef


@pytest.fixture
def relevance() -> RockRelevancePolicy:
    return RockRelevancePolicy()


@pytest.fixture
def normalizer(relevance: RockRelevancePolicy) -> PodcastNormalizer:
    return PodcastNormalizer(relevance)


@pytest.fixture
def raw_record() -> RawPodcastRecord:
    return RawPodcastRecordFactory.build(external_id="1001")


@pytest.fixture
def expected_podcast() -> Podcast:
    """What `raw_record` must look like once normalized."""
    return Podcast(
        ref=ExternalRef(source="itunes", external_id="1001"),
        title="Classic Rock Hour",
        author="Rock Radio Network",
        description="Stories behind the greatest rock records.",
        language="en-US",
        country="USA",
        genres=("Music", "Music History"),
        primary_genre="Music",
        feed_url="https://feeds.example.com/classic-rock.xml",
        store_url="https://podcasts.apple.com/podcast/id1000",
        cover_image_url="https://images.example.com/classic-rock.jpg",
        explicit=False,
        episode_count=120,
        released_at=datetime(2026, 9, 1, 10, 0, tzinfo=UTC),
    )
