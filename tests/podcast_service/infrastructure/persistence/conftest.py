from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from factories import PodcastFactory
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
    """Four stored podcasts covering the search, genre and language filters."""
    podcasts = [
        PodcastFactory.build(
            title="Classic Rock Hour",
            author="Rock Radio",
            genres=("Music", "Music History"),
            language="en-US",
        ),
        PodcastFactory.build(
            title="Punk Tapes", author="Garage Collective", genres=("Music",), language="en-GB"
        ),
        PodcastFactory.build(
            title="Rock Nacional",
            author="Radio Buenos Aires",
            genres=("Music", "Music Commentary"),
            language="es-AR",
        ),
        PodcastFactory.build(
            title="Metal 100%_Loud", author="Heavy Co", genres=("Music",), language=None
        ),
    ]
    return [(await repository.upsert(podcast))[0] for podcast in podcasts]
