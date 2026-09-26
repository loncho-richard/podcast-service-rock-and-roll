from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from factories import PodcastFactory, build_catalog
from podcast_service.domain.podcast.entities import Podcast
from podcast_service.infrastructure.persistence.database import create_session_factory
from podcast_service.infrastructure.persistence.podcast_repository import (
    SqlAlchemyPodcastRepository,
)
from podcast_service.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def session_factory(database: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return create_session_factory(database)


@pytest.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@pytest.fixture
def repository(session: AsyncSession) -> SqlAlchemyPodcastRepository:
    return SqlAlchemyPodcastRepository(session)


@pytest.fixture
def unit_of_work(session_factory: async_sessionmaker[AsyncSession]) -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(session_factory)


@pytest.fixture
def podcast() -> Podcast:
    return PodcastFactory.build()


@pytest.fixture
async def catalog(repository: SqlAlchemyPodcastRepository) -> list[Podcast]:
    return [(await repository.upsert(podcast))[0] for podcast in build_catalog()]
