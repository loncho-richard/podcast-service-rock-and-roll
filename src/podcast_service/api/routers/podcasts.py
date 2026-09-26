from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from podcast_service.api.errors import COMMON_ERRORS, error_responses
from podcast_service.api.exporters import ExportFormat, export_stream
from podcast_service.api.schemas.podcasts import PodcastPage, PodcastResponse
from podcast_service.api.security import require_auth
from podcast_service.application.podcast.queries import ExportPodcasts, GetPodcast, ListPodcasts
from podcast_service.container import Container
from podcast_service.domain.podcast.filters import PageRequest, PodcastFilters

router = APIRouter(
    prefix="/podcasts",
    tags=["podcasts"],
    dependencies=[Depends(require_auth)],
    responses=COMMON_ERRORS,
)


@router.get("", summary="List podcasts (paginated, filterable)")
@inject
async def list_podcasts(
    q: Annotated[
        str | None,
        Query(
            max_length=100,
            description="Case-insensitive match on title or author; blank is ignored.",
        ),
    ] = None,
    genre: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=100,
            description="Exact, case-sensitive genre as returned by the API, e.g. `Music History`.",
        ),
    ] = None,
    language: Annotated[
        str | None,
        Query(
            pattern=r"^[A-Za-z]{2,3}(-[A-Za-z0-9]{2,8})?$",
            description="Language tag; `en` also matches regional variants such as `en-US`.",
        ),
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    use_case: ListPodcasts = Depends(Provide[Container.list_podcasts]),
) -> PodcastPage:
    result = await use_case.execute(
        PodcastFilters(query=(q or "").strip() or None, genre=genre, language=language),
        PageRequest(page=page, page_size=page_size),
    )
    return PodcastPage.from_domain(result)


# Declared before `/{podcast_id}` so "export" is not parsed as an id.
@router.get(
    "/export",
    summary="Export the whole catalog (streamed)",
    description=(
        "Streams every podcast as NDJSON (one JSON object per line, default) or CSV "
        "(list fields joined with `|`). Rows are read through a server-side cursor and "
        "written as they arrive, so memory stays flat however large the catalog is."
    ),
    response_class=StreamingResponse,
    responses={
        200: {
            "description": "The catalog, ordered by title.",
            "content": {"application/x-ndjson": {}, "text/csv": {}},
        }
    },
)
@inject
async def export_podcasts(
    export_format: Annotated[ExportFormat, Query(alias="format")] = ExportFormat.NDJSON,
    use_case: ExportPodcasts = Depends(Provide[Container.export_podcasts]),
) -> StreamingResponse:
    return StreamingResponse(
        export_stream(use_case.execute(), export_format),
        media_type=export_format.media_type,
        headers={"Content-Disposition": f'attachment; filename="podcasts.{export_format.value}"'},
    )


@router.get(
    "/{podcast_id}",
    summary="Get a podcast by id",
    responses=error_responses(HTTPStatus.NOT_FOUND),
)
@inject
async def get_podcast(
    podcast_id: UUID,
    use_case: GetPodcast = Depends(Provide[Container.get_podcast]),
) -> PodcastResponse:
    return PodcastResponse.from_domain(await use_case.execute(podcast_id))
