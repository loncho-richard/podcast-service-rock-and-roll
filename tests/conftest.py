from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from podcast_service.api.app import create_app
from podcast_service.config import Settings
from podcast_service.container import Container


@pytest.fixture
def settings() -> Settings:
    # `_env_file=None` keeps a developer's local `.env` from leaking into tests.
    return Settings(_env_file=None)  # type: ignore[call-arg]


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
