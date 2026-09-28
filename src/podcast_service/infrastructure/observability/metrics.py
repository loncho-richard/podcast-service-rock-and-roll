from prometheus_client import Counter, Histogram

from podcast_service.domain.ingestion import IngestionSummary
from podcast_service.domain.podcast import UpsertOutcome

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "HTTP requests handled, by route template and status code.",
    ["method", "route", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Time to handle a request, until the last byte of the response.",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)

BULK_INGESTIONS = Counter(
    "bulk_ingestions_total",
    "Bulk ingestions run, by where the data came from (live source or offline sample).",
    ["source"],
)
INGESTED_PODCASTS = Counter(
    "ingested_podcasts_total",
    "Podcasts processed by ingestion (bulk and single), by outcome.",
    ["outcome"],
)
PALETTE_FAILURES = Counter(
    "palette_failures_total",
    "Stored podcasts whose cover could not be turned into a color palette.",
)

UPSTREAM_REQUESTS = Counter(
    "upstream_requests_total",
    "Calls to third-party services after retries, by service and result.",
    ["upstream", "outcome"],
)
ITUNES_FALLBACKS = Counter(
    "itunes_fallbacks_total",
    "Times the offline iTunes sample was served because the live API was unavailable.",
    ["operation"],
)


RATE_LIMITED_CALLS = Counter(
    "rate_limited_calls_total",
    "Calls held back by our own rate limiter: delayed, or rejected past the max wait.",
    ["upstream", "outcome"],
)


def record_rate_limit(upstream: str, *, waited: bool) -> None:
    RATE_LIMITED_CALLS.labels(upstream, "waited" if waited else "rejected").inc()


def record_upstream(upstream: str, *, succeeded: bool) -> None:
    UPSTREAM_REQUESTS.labels(upstream, "success" if succeeded else "failure").inc()


def record_bulk_ingestion(summary: IngestionSummary) -> None:
    BULK_INGESTIONS.labels(summary.source_mode.value).inc()
    for outcome, count in (
        (UpsertOutcome.CREATED.value, summary.created),
        (UpsertOutcome.UPDATED.value, summary.updated),
        (UpsertOutcome.UNCHANGED.value, summary.unchanged),
        ("skipped", summary.skipped),
    ):
        INGESTED_PODCASTS.labels(outcome).inc(count)
    PALETTE_FAILURES.inc(summary.palette_failures)


def record_single_ingestion(outcome: UpsertOutcome, *, palette_failed: bool) -> None:
    INGESTED_PODCASTS.labels(outcome.value).inc()
    if palette_failed:
        PALETTE_FAILURES.inc()
