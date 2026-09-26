from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from podcast_service.api.schemas.podcasts import PodcastResponse
from podcast_service.application.ingestion.single_ingest import SingleIngestionResult
from podcast_service.domain.ingestion.summary import IngestionSummary, SkipReason, SourceMode
from podcast_service.domain.podcast.repository import UpsertOutcome

SearchTerm = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class BulkIngestionRequest(BaseModel):
    terms: list[SearchTerm] | None = Field(
        default=None,
        min_length=1,
        max_length=20,
        description="Search terms; omit to use the configured rock & roll terms.",
        examples=[["classic rock", "punk rock"]],
    )
    limit: int = Field(
        default=25, ge=1, le=200, description="Maximum results per term (iTunes caps at 200)."
    )


class SkippedRecordResponse(BaseModel):
    external_id: str | None
    title: str | None
    reason: SkipReason


class IngestionSummaryResponse(BaseModel):
    source: SourceMode = Field(
        description="`fallback` when the live source was unavailable and the stored sample "
        "was ingested instead."
    )
    fetched: int = Field(description="Distinct records received from the source.")
    stored: int = Field(description="created + updated + unchanged.")
    created: int
    updated: int
    unchanged: int = Field(description="Already stored with identical data.")
    skipped: int
    palette_failures: int = Field(
        description="Stored podcasts whose cover could not be turned into a palette."
    )
    skipped_records: list[SkippedRecordResponse]

    @classmethod
    def from_domain(cls, summary: IngestionSummary) -> "IngestionSummaryResponse":
        return cls(
            source=summary.source_mode,
            fetched=summary.fetched,
            stored=summary.stored,
            created=summary.created,
            updated=summary.updated,
            unchanged=summary.unchanged,
            skipped=summary.skipped,
            palette_failures=summary.palette_failures,
            skipped_records=[
                SkippedRecordResponse(
                    external_id=record.external_id, title=record.title, reason=record.reason
                )
                for record in summary.skipped_records
            ],
        )


class SingleIngestionResponse(BaseModel):
    outcome: UpsertOutcome
    palette_failed: bool
    podcast: PodcastResponse

    @classmethod
    def from_domain(cls, result: SingleIngestionResult) -> "SingleIngestionResponse":
        return cls(
            outcome=result.outcome,
            palette_failed=result.palette_failed,
            podcast=PodcastResponse.from_domain(result.podcast),
        )
