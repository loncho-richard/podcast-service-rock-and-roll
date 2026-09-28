from http import HTTPStatus
from typing import Annotated

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Body, Depends, Path, Response

from podcast_service.api import COMMON_ERRORS, error_responses, require_auth
from podcast_service.api.schemas import (
    BulkIngestionRequest,
    IngestionSummaryResponse,
    SingleIngestionResponse,
)
from podcast_service.application.ingestion import BulkIngestPodcasts, IngestSinglePodcast
from podcast_service.container import Container
from podcast_service.domain.podcast import UpsertOutcome
from podcast_service.infrastructure.observability import (
    record_bulk_ingestion,
    record_single_ingestion,
)

router = APIRouter(
    prefix="/ingestion",
    tags=["ingestion"],
    dependencies=[Depends(require_auth)],
    responses=COMMON_ERRORS,
)


@router.post(
    "/bulk",
    summary="Ingest a batch of rock & roll podcasts from iTunes",
    description=(
        "Searches the source, cleans and stores the results, downloading each cover to "
        "extract its color palette. Idempotent: re-running it updates existing podcasts "
        "instead of duplicating them. If the source is unavailable, a stored sample of "
        "real responses is ingested instead (`source: fallback`)."
    ),
)
@inject
async def bulk_ingest(
    request: Annotated[BulkIngestionRequest | None, Body()] = None,
    use_case: BulkIngestPodcasts = Depends(Provide[Container.bulk_ingest]),
) -> IngestionSummaryResponse:
    request = request or BulkIngestionRequest()
    summary = await use_case.execute(terms=request.terms, limit=request.limit)
    record_bulk_ingestion(summary)
    return IngestionSummaryResponse.from_domain(summary)


@router.post(
    "/podcasts/{itunes_id}",
    summary="Ingest a single podcast by its iTunes id",
    description=(
        "`201` when the podcast is new, `200` when it already existed (updated or "
        "unchanged). `422` when the podcast exists but is rejected, e.g. not rock & roll."
    ),
    status_code=HTTPStatus.OK,
    responses={
        HTTPStatus.CREATED: {"model": SingleIngestionResponse, "description": "Created."},
        **error_responses(HTTPStatus.NOT_FOUND, HTTPStatus.SERVICE_UNAVAILABLE),
    },
)
@inject
async def ingest_single(
    itunes_id: Annotated[str, Path(pattern=r"^\d{1,20}$", examples=["1618650164"])],
    response: Response,
    use_case: IngestSinglePodcast = Depends(Provide[Container.ingest_single]),
) -> SingleIngestionResponse:
    result = await use_case.execute(itunes_id)
    record_single_ingestion(result.outcome, palette_failed=result.palette_failed)
    if result.outcome is UpsertOutcome.CREATED:
        response.status_code = HTTPStatus.CREATED.value
    return SingleIngestionResponse.from_domain(result)
