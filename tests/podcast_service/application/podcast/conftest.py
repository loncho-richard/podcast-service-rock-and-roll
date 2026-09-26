import pytest

from factories import build_catalog
from fakes import InMemoryPodcastRepository, InMemoryUnitOfWork
from podcast_service.application.podcast import ExportPodcasts, GetPodcast, ListPodcasts
from podcast_service.domain.podcast import Podcast


@pytest.fixture
def repository() -> InMemoryPodcastRepository:
    return InMemoryPodcastRepository()


@pytest.fixture
def unit_of_work(repository: InMemoryPodcastRepository) -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork(repository)


@pytest.fixture
async def stored_catalog(repository: InMemoryPodcastRepository) -> list[Podcast]:
    return [(await repository.upsert(podcast))[0] for podcast in build_catalog()]


@pytest.fixture
def list_podcasts(unit_of_work: InMemoryUnitOfWork) -> ListPodcasts:
    return ListPodcasts(lambda: unit_of_work)


@pytest.fixture
def get_podcast(unit_of_work: InMemoryUnitOfWork) -> GetPodcast:
    return GetPodcast(lambda: unit_of_work)


@pytest.fixture
def export_podcasts(unit_of_work: InMemoryUnitOfWork) -> ExportPodcasts:
    return ExportPodcasts(lambda: unit_of_work)
