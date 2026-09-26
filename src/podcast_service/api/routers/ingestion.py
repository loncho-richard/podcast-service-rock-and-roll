from http import HTTPStatus
from typing import Annotated, Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Body, Depends, Path, Response

from podcast_service.api.errors import ERROR_RESPONSES
from podcast_service.api.schemas.errors import ErrorResponse
from podcast_service.api.schemas.ingestion import (
    BulkIngestionRequest,
    IngestionSummaryResponse,
    SingleIngestionResponse,
)
from podcast_service.api.security import require_auth
from podcast_service.application.ingestion.bulk_ingest import BulkIngestPodcasts
from podcast_service.application.ingestion.single_ingest import IngestSinglePodcast
from podcast_service.container import Container
from podcast_service.domain.podcast.repository import UpsertOutcome

router = APIRouter(
    prefix="/ingestion",
    tags=["ingestion"],
    dependencies=[Depends(require_auth)],
    responses=ERROR_RESPONSES,
)

_SOURCE_UNAVAILABLE: dict[int | str, dict[str, Any]] = {
    HTTPStatus.SERVICE_UNAVAILABLE: {
        "model": ErrorResponse,
        "description": "The source is down and the podcast is not in the offline sample.",
    }
}


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
    return IngestionSummaryResponse.from_domain(summary)


@router.post(
    "/podcasts/{itunes_id}",
    summary="Ingest a single podcast by its iTunes id",
    description=(
        "`201` when the podcast is new, `200` when it already existed (updated or "
        "unchanged). `422` when the podcast exists but is rejected, e.g. not rock & roll."
    ),
    status_code=HTTPStatus.OK,
    responses={HTTPStatus.CREATED: {"model": SingleIngestionResponse}, **_SOURCE_UNAVAILABLE},
)
@inject
async def ingest_single(
    itunes_id: Annotated[str, Path(pattern=r"^\d{1,20}$", examples=["1618650164"])],
    response: Response,
    use_case: IngestSinglePodcast = Depends(Provide[Container.ingest_single]),
) -> SingleIngestionResponse:
    result = await use_case.execute(itunes_id)
    if result.outcome is UpsertOutcome.CREATED:
        response.status_code = HTTPStatus.CREATED.value
    return SingleIngestionResponse.from_domain(result)
