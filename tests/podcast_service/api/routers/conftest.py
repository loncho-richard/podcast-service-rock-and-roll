import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from factories import build_catalog
from podcast_service.domain.podcast import Podcast
from podcast_service.infrastructure.persistence import SqlAlchemyUnitOfWork, create_session_factory


@pytest.fixture
async def stored_catalog(live_database: AsyncEngine) -> list[Podcast]:
    """The four-podcast catalog, committed to the database the app is using."""
    async with SqlAlchemyUnitOfWork(create_session_factory(live_database)) as uow:
        stored = [(await uow.podcasts.upsert(podcast))[0] for podcast in build_catalog()]
        await uow.commit()
    return stored
