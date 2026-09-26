from collections.abc import Callable
from dataclasses import dataclass

from podcast_service.application import UnitOfWork
from podcast_service.application.ingestion.enrichment import PodcastEnricher
from podcast_service.domain.ingestion import (
    PodcastNormalizer,
    PodcastRejectedError,
    PodcastSource,
    SkippedRecord,
)
from podcast_service.domain.podcast import Podcast, UpsertOutcome
from podcast_service.domain.shared import NotFoundError


@dataclass(frozen=True, slots=True)
class SingleIngestionResult:
    podcast: Podcast
    outcome: UpsertOutcome
    palette_failed: bool


class IngestSinglePodcast:
    """Ingest one podcast on demand by its id in the source."""

    def __init__(
        self,
        source: PodcastSource,
        normalizer: PodcastNormalizer,
        enricher: PodcastEnricher,
        uow_factory: Callable[[], UnitOfWork],
    ) -> None:
        self._source = source
        self._normalizer = normalizer
        self._enricher = enricher
        self._uow_factory = uow_factory

    async def execute(self, external_id: str) -> SingleIngestionResult:
        raw = await self._source.lookup(external_id)
        if raw is None:
            raise NotFoundError(f"Podcast {external_id} was not found in the source.")

        normalized = self._normalizer.normalize(raw)
        if isinstance(normalized, SkippedRecord):
            raise PodcastRejectedError(
                f"Podcast {external_id} was rejected: {normalized.reason.value}."
            )

        enriched = await self._enricher.enrich(normalized)
        async with self._uow_factory() as uow:
            stored, outcome = await uow.podcasts.upsert(enriched.podcast)
            await uow.commit()
        return SingleIngestionResult(stored, outcome, enriched.palette_failed)
