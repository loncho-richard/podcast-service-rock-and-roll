from podcast_service.domain.ingestion.summary import (
    IngestionSummary,
    SkippedRecord,
    SkipReason,
    SourceMode,
)


def test_stored_and_skipped_totals_are_derived() -> None:
    summary = IngestionSummary(
        source_mode=SourceMode.LIVE,
        fetched=5,
        created=2,
        updated=1,
        skipped_records=(
            SkippedRecord(SkipReason.MISSING_TITLE, "1"),
            SkippedRecord(SkipReason.NOT_ROCK_RELATED, "2"),
        ),
    )

    assert (summary.stored, summary.skipped) == (3, 2)
