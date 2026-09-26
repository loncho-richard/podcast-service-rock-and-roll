"""Ingestion rules: normalization, rock relevance, summary and outbound ports."""

from podcast_service.domain.ingestion.errors import PodcastRejectedError, SourceUnavailableError
from podcast_service.domain.ingestion.normalizer import PodcastNormalizer
from podcast_service.domain.ingestion.ports import (
    FeedDetails,
    FeedReader,
    ImageFetcher,
    PaletteExtractor,
    PodcastSource,
    SourceBatch,
)
from podcast_service.domain.ingestion.raw import RawPodcastRecord
from podcast_service.domain.ingestion.relevance import RockRelevancePolicy
from podcast_service.domain.ingestion.summary import (
    IngestionSummary,
    SkippedRecord,
    SkipReason,
    SourceMode,
)

__all__ = [
    "FeedDetails",
    "FeedReader",
    "ImageFetcher",
    "IngestionSummary",
    "PaletteExtractor",
    "PodcastNormalizer",
    "PodcastRejectedError",
    "PodcastSource",
    "RawPodcastRecord",
    "RockRelevancePolicy",
    "SkipReason",
    "SkippedRecord",
    "SourceBatch",
    "SourceMode",
    "SourceUnavailableError",
]
