from collections.abc import Callable

from podcast_service.domain.ingestion import (
    IngestionSummary,
    SkippedRecord,
    SkipReason,
    SourceMode,
)
from podcast_service.domain.podcast import UpsertOutcome
from podcast_service.infrastructure.observability import (
    record_bulk_ingestion,
    record_single_ingestion,
)


def test_bulk_ingestion_is_counted_by_source_and_outcome(
    metric_delta: Callable[..., Callable[[], float]],
) -> None:
    deltas = {
        "fallback_runs": metric_delta("bulk_ingestions_total", source="fallback"),
        "created": metric_delta("ingested_podcasts_total", outcome="created"),
        "unchanged": metric_delta("ingested_podcasts_total", outcome="unchanged"),
        "skipped": metric_delta("ingested_podcasts_total", outcome="skipped"),
        "palette_failures": metric_delta("palette_failures_total"),
    }

    record_bulk_ingestion(
        IngestionSummary(
            source_mode=SourceMode.FALLBACK,
            fetched=6,
            created=3,
            unchanged=2,
            palette_failures=1,
            skipped_records=(SkippedRecord(SkipReason.NOT_ROCK_RELATED, "9"),),
        )
    )

    assert {name: delta() for name, delta in deltas.items()} == {
        "fallback_runs": 1,
        "created": 3,
        "unchanged": 2,
        "skipped": 1,
        "palette_failures": 1,
    }


def test_single_ingestion_is_counted(metric_delta: Callable[..., Callable[[], float]]) -> None:
    updated = metric_delta("ingested_podcasts_total", outcome="updated")
    palette_failures = metric_delta("palette_failures_total")

    record_single_ingestion(UpsertOutcome.UPDATED, palette_failed=True)

    assert (updated(), palette_failures()) == (1, 1)
