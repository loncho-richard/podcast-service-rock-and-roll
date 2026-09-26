"""Request and response models (the public JSON contract)."""

from podcast_service.api.schemas.auth import TokenResponse
from podcast_service.api.schemas.errors import ErrorDetail, ErrorResponse
from podcast_service.api.schemas.health import HealthResponse
from podcast_service.api.schemas.ingestion import (
    BulkIngestionRequest,
    IngestionSummaryResponse,
    SingleIngestionResponse,
    SkippedRecordResponse,
)
from podcast_service.api.schemas.podcasts import PodcastPage, PodcastResponse

__all__ = [
    "BulkIngestionRequest",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "IngestionSummaryResponse",
    "PodcastPage",
    "PodcastResponse",
    "SingleIngestionResponse",
    "SkippedRecordResponse",
    "TokenResponse",
]
