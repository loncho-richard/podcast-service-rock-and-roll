from collections.abc import AsyncIterator, Callable
from uuid import UUID

from podcast_service.application import UnitOfWork
from podcast_service.domain.podcast import Page, PageRequest, Podcast, PodcastFilters
from podcast_service.domain.shared import NotFoundError


class ListPodcasts:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, filters: PodcastFilters, page: PageRequest) -> Page[Podcast]:
        async with self._uow_factory() as uow:
            return await uow.podcasts.list(filters, page)


class GetPodcast:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self, podcast_id: UUID) -> Podcast:
        async with self._uow_factory() as uow:
            podcast = await uow.podcasts.get(podcast_id)
        if podcast is None:
            raise NotFoundError(f"Podcast {podcast_id} was not found.")
        return podcast


class ExportPodcasts:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    async def execute(self) -> AsyncIterator[Podcast]:
        """Stream the whole catalog. The unit of work (and its DB cursor) stays open
        only while the caller keeps consuming, and closes if it stops early."""
        async with self._uow_factory() as uow:
            async for podcast in uow.podcasts.stream_all():
                yield podcast
