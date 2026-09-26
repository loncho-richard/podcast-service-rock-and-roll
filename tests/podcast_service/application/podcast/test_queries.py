from uuid import uuid4

import pytest

from fakes import InMemoryUnitOfWork
from podcast_service.application.podcast import ExportPodcasts, GetPodcast, ListPodcasts
from podcast_service.domain.podcast import PageRequest, Podcast, PodcastFilters
from podcast_service.domain.shared import NotFoundError


async def test_list_returns_the_requested_page(
    list_podcasts: ListPodcasts, stored_catalog: list[Podcast]
) -> None:
    page = await list_podcasts.execute(PodcastFilters(), PageRequest(page=1, page_size=2))

    assert (page.total, [p.title for p in page.items]) == (
        4,
        ["Classic Rock Hour", "Metal 100%_Loud"],
    )


async def test_get_returns_the_podcast(
    get_podcast: GetPodcast, stored_catalog: list[Podcast]
) -> None:
    podcast = stored_catalog[0]
    assert podcast.id is not None

    assert await get_podcast.execute(podcast.id) == podcast


async def test_get_unknown_podcast_raises_not_found(get_podcast: GetPodcast) -> None:
    with pytest.raises(NotFoundError):
        await get_podcast.execute(uuid4())


@pytest.mark.usefixtures("stored_catalog")
async def test_export_streams_every_podcast(export_podcasts: ExportPodcasts) -> None:
    titles = [podcast.title async for podcast in export_podcasts.execute()]

    assert titles == ["Classic Rock Hour", "Metal 100%_Loud", "Punk Tapes", "Rock Nacional"]


@pytest.mark.usefixtures("stored_catalog")
async def test_export_releases_the_unit_of_work_when_the_client_stops_early(
    export_podcasts: ExportPodcasts, unit_of_work: InMemoryUnitOfWork
) -> None:
    stream = export_podcasts.execute()
    await anext(stream)

    await stream.aclose()  # what Starlette does when the client disconnects

    assert unit_of_work.exits == 1
