import pytest

from fakes import UNAVAILABLE_ID
from podcast_service.application.ingestion.single_ingest import IngestSinglePodcast
from podcast_service.domain.ingestion.errors import PodcastRejectedError, SourceUnavailableError
from podcast_service.domain.podcast.repository import UpsertOutcome
from podcast_service.domain.shared.exceptions import DomainError, NotFoundError


async def test_new_podcast_is_created_and_enriched(ingest_single: IngestSinglePodcast) -> None:
    result = await ingest_single.execute("1001")

    assert (result.outcome, result.palette_failed, result.podcast.description) == (
        UpsertOutcome.CREATED,
        False,
        "From the feed",
    )


async def test_ingesting_the_same_podcast_again_changes_nothing(
    ingest_single: IngestSinglePodcast,
) -> None:
    first = await ingest_single.execute("1001")

    second = await ingest_single.execute("1001")

    assert (second.outcome, second.podcast.id) == (UpsertOutcome.UNCHANGED, first.podcast.id)


async def test_broken_cover_is_reported_not_raised(ingest_single: IngestSinglePodcast) -> None:
    result = await ingest_single.execute("1002")

    assert (result.outcome, result.palette_failed) == (UpsertOutcome.CREATED, True)


@pytest.mark.parametrize(
    ("external_id", "error", "message"),
    [
        ("9999", NotFoundError, "not found"),
        ("1003", PodcastRejectedError, "not_rock_related"),
        ("1004", PodcastRejectedError, "missing_title"),
        (UNAVAILABLE_ID, SourceUnavailableError, "unavailable"),
    ],
    ids=["unknown", "not-rock", "invalid-record", "source-down"],
)
async def test_podcasts_that_cannot_be_ingested_raise(
    ingest_single: IngestSinglePodcast,
    external_id: str,
    error: type[DomainError],
    message: str,
) -> None:
    with pytest.raises(error, match=message):
        await ingest_single.execute(external_id)
