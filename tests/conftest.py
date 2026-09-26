from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.community.postgres import PostgresContainer

from podcast_service.api.app import create_app
from podcast_service.config import Settings
from podcast_service.container import Container
from podcast_service.infrastructure.persistence.database import create_engine

_ALEMBIC_INI = Path(__file__).parents[1] / "alembic.ini"
_UNREACHABLE_DATABASE_URL = "postgresql+asyncpg://nobody:nothing@127.0.0.1:1/nothing"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Any test that (transitively) needs PostgreSQL is an integration test."""
    for item in items:
        if "postgres_url" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.integration)


# --- application -------------------------------------------------------------


@pytest.fixture
def settings() -> Settings:
    # `_env_file=None` keeps a developer's local `.env` from leaking into tests.
    return Settings(_env_file=None, database_url=_UNREACHABLE_DATABASE_URL)  # type: ignore[call-arg]


@pytest.fixture
def container(settings: Settings) -> Container:
    container = Container()
    container.settings.override(settings)
    return container


@pytest.fixture
def app(container: Container) -> FastAPI:
    return create_app(container)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


# --- database (Docker via testcontainers) -------------------------------------


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as postgres:
        url = postgres.get_connection_url()
        config = Config(_ALEMBIC_INI)
        config.set_main_option("sqlalchemy.url", url)
        config.attributes["configure_logger"] = False
        command.upgrade(config, "head")  # the real migrations are part of what we test
        yield url


@pytest.fixture(scope="session")
async def db_engine(postgres_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_engine(postgres_url)
    yield engine
    await engine.dispose()


@pytest.fixture
async def database(db_engine: AsyncEngine) -> AsyncIterator[AsyncEngine]:
    """A migrated database that is emptied after each test."""
    yield db_engine
    async with db_engine.begin() as connection:
        await connection.execute(text("TRUNCATE podcasts"))


@pytest.fixture
def live_database(container: Container, database: AsyncEngine) -> AsyncEngine:
    """Point the application at the test database."""
    container.engine.override(database)
    return database
