import pytest

from fakes import FakePodcastSource, InMemoryPodcastRepository, InMemoryUnitOfWork, upstream_records
from podcast_service.application.ingestion.bulk_ingest import BulkIngestPodcasts
from podcast_service.application.ingestion.enrichment import PodcastEnricher
from podcast_service.application.ingestion.single_ingest import IngestSinglePodcast
from podcast_service.domain.ingestion.normalizer import PodcastNormalizer
from podcast_service.domain.ingestion.summary import SourceMode


@pytest.fixture
def repository() -> InMemoryPodcastRepository:
    return InMemoryPodcastRepository()


@pytest.fixture
def unit_of_work(repository: InMemoryPodcastRepository) -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork(repository)


@pytest.fixture
def fallback_source() -> FakePodcastSource:
    return FakePodcastSource(upstream_records(), mode=SourceMode.FALLBACK)


def _bulk_ingest(
    source: FakePodcastSource,
    normalizer: PodcastNormalizer,
    enricher: PodcastEnricher,
    unit_of_work: InMemoryUnitOfWork,
) -> BulkIngestPodcasts:
    return BulkIngestPodcasts(
        source=source,
        normalizer=normalizer,
        enricher=enricher,
        uow_factory=lambda: unit_of_work,
        default_terms=["rock"],
    )


@pytest.fixture
def bulk_ingest(
    fake_source: FakePodcastSource,
    normalizer: PodcastNormalizer,
    enricher: PodcastEnricher,
    unit_of_work: InMemoryUnitOfWork,
) -> BulkIngestPodcasts:
    return _bulk_ingest(fake_source, normalizer, enricher, unit_of_work)


@pytest.fixture
def bulk_ingest_from_fallback(
    fallback_source: FakePodcastSource,
    normalizer: PodcastNormalizer,
    enricher: PodcastEnricher,
    unit_of_work: InMemoryUnitOfWork,
) -> BulkIngestPodcasts:
    return _bulk_ingest(fallback_source, normalizer, enricher, unit_of_work)


@pytest.fixture
def ingest_single(
    fake_source: FakePodcastSource,
    normalizer: PodcastNormalizer,
    enricher: PodcastEnricher,
    unit_of_work: InMemoryUnitOfWork,
) -> IngestSinglePodcast:
    return IngestSinglePodcast(
        source=fake_source,
        normalizer=normalizer,
        enricher=enricher,
        uow_factory=lambda: unit_of_work,
    )
