from podcast_service.domain.podcast.entities import Podcast
from podcast_service.domain.podcast.filters import PageRequest, PodcastFilters
from podcast_service.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


async def _count(unit_of_work: SqlAlchemyUnitOfWork) -> int:
    async with unit_of_work as uow:
        return (await uow.podcasts.list(PodcastFilters(), PageRequest())).total


async def test_committed_changes_are_persisted(
    unit_of_work: SqlAlchemyUnitOfWork, podcast: Podcast
) -> None:
    async with unit_of_work as uow:
        await uow.podcasts.upsert(podcast)
        await uow.commit()

    assert await _count(unit_of_work) == 1


async def test_changes_without_commit_are_rolled_back(
    unit_of_work: SqlAlchemyUnitOfWork, podcast: Podcast
) -> None:
    async with unit_of_work as uow:
        await uow.podcasts.upsert(podcast)

    assert await _count(unit_of_work) == 0
