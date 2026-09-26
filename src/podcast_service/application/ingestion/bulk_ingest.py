import logging
from collections import Counter
from collections.abc import Callable, Sequence

from podcast_service.application.ingestion.enrichment import PodcastEnricher
from podcast_service.application.unit_of_work import UnitOfWork
from podcast_service.domain.ingestion.normalizer import PodcastNormalizer
from podcast_service.domain.ingestion.ports import PodcastSource
from podcast_service.domain.ingestion.summary import IngestionSummary
from podcast_service.domain.podcast.repository import UpsertOutcome

logger = logging.getLogger(__name__)


class BulkIngestPodcasts:
    """Fetch -> normalize -> enrich -> upsert. Safe to run repeatedly (idempotent)."""

    def __init__(
        self,
        source: PodcastSource,
        normalizer: PodcastNormalizer,
        enricher: PodcastEnricher,
        uow_factory: Callable[[], UnitOfWork],
        default_terms: Sequence[str],
    ) -> None:
        self._source = source
        self._normalizer = normalizer
        self._enricher = enricher
        self._uow_factory = uow_factory
        self._default_terms = default_terms

    async def execute(self, terms: Sequence[str] | None, limit: int) -> IngestionSummary:
        batch = await self._source.search(terms or self._default_terms, limit)
        podcasts, skipped = self._normalizer.normalize_batch(batch.records)
        # Network-bound enrichment happens before the transaction is opened.
        enriched = await self._enricher.enrich_many(podcasts)

        outcomes: Counter[UpsertOutcome] = Counter()
        async with self._uow_factory() as uow:
            for result in enriched:
                _, outcome = await uow.podcasts.upsert(result.podcast)
                outcomes[outcome] += 1
            await uow.commit()

        summary = IngestionSummary(
            source_mode=batch.mode,
            fetched=len(batch.records),
            created=outcomes[UpsertOutcome.CREATED],
            updated=outcomes[UpsertOutcome.UPDATED],
            unchanged=outcomes[UpsertOutcome.UNCHANGED],
            palette_failures=sum(result.palette_failed for result in enriched),
            skipped_records=tuple(skipped),
        )
        logger.info(
            "Bulk ingestion (%s): fetched=%d created=%d updated=%d unchanged=%d skipped=%d "
            "palette_failures=%d",
            summary.source_mode,
            summary.fetched,
            summary.created,
            summary.updated,
            summary.unchanged,
            summary.skipped,
            summary.palette_failures,
        )
        for record in summary.skipped_records:
            logger.info("Skipped %s (%s): %s", record.external_id, record.title, record.reason)
        return summary
