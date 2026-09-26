import pytest

from fakes import COVER_PALETTE, FakePodcastSource, InMemoryPodcastRepository, InMemoryUnitOfWork
from podcast_service.application.ingestion import BulkIngestPodcasts
from podcast_service.domain.ingestion import IngestionSummary, SkippedRecord, SkipReason, SourceMode
from podcast_service.domain.podcast import ExternalRef

EXPECTED_SKIPPED = (
    SkippedRecord(SkipReason.NOT_ROCK_RELATED, "1003", "Jazz Standards"),
    SkippedRecord(SkipReason.MISSING_TITLE, "1004", None),
    SkippedRecord(SkipReason.DUPLICATE_IN_BATCH, "1001", "Classic Rock Hour (mirror)"),
)


async def test_first_run_stores_valid_podcasts_and_explains_the_rest(
    bulk_ingest: BulkIngestPodcasts,
) -> None:
    summary = await bulk_ingest.execute(terms=None, limit=25)

    assert summary == IngestionSummary(
        source_mode=SourceMode.LIVE,
        fetched=5,
        created=2,
        palette_failures=1,  # "Punk Tapes" has a broken cover but is still stored
        skipped_records=EXPECTED_SKIPPED,
    )


async def test_running_again_is_idempotent(
    bulk_ingest: BulkIngestPodcasts, repository: InMemoryPodcastRepository
) -> None:
    await bulk_ingest.execute(terms=None, limit=25)

    second = await bulk_ingest.execute(terms=None, limit=25)

    assert (second.created, second.unchanged, len(repository.podcasts)) == (0, 2, 2)


async def test_stored_podcasts_carry_feed_details_and_palette(
    bulk_ingest: BulkIngestPodcasts, repository: InMemoryPodcastRepository
) -> None:
    await bulk_ingest.execute(terms=None, limit=25)

    stored = repository.podcasts[ExternalRef("itunes", "1001")]
    assert (stored.description, stored.language, stored.palette) == (
        "From the feed",
        "en-GB",
        COVER_PALETTE,
    )


@pytest.mark.parametrize(
    ("terms", "expected_terms"),
    [(None, ["rock"]), (["punk rock"], ["punk rock"])],
    ids=["defaults", "requested"],
)
async def test_searches_requested_or_default_terms(
    bulk_ingest: BulkIngestPodcasts,
    fake_source: FakePodcastSource,
    terms: list[str] | None,
    expected_terms: list[str],
) -> None:
    await bulk_ingest.execute(terms=terms, limit=25)

    assert fake_source.searched_terms == expected_terms


async def test_reports_when_the_fallback_sample_was_ingested(
    bulk_ingest_from_fallback: BulkIngestPodcasts,
) -> None:
    summary = await bulk_ingest_from_fallback.execute(terms=None, limit=25)

    assert summary.source_mode is SourceMode.FALLBACK


async def test_the_whole_batch_is_committed_once(
    bulk_ingest: BulkIngestPodcasts, unit_of_work: InMemoryUnitOfWork
) -> None:
    await bulk_ingest.execute(terms=None, limit=25)

    assert unit_of_work.commits == 1
