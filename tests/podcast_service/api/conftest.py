from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import UUID

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from factories import PodcastFactory
from podcast_service.api import (
    RequestContextMiddleware,
    register_exception_handlers,
    require_auth,
)
from podcast_service.container import Container
from podcast_service.domain.podcast import ExternalRef, Podcast
from podcast_service.domain.shared import DomainError, NotFoundError
from podcast_service.infrastructure.observability import request_id_var


@pytest.fixture
def errors_app() -> FastAPI:
    """Minimal app whose routes fail in every way the error handlers must cover."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/not-found")
    async def not_found() -> None:
        raise NotFoundError("Podcast 42 was not found.")

    @app.get("/domain-error")
    async def domain_error() -> None:
        raise DomainError("Business rule broken.")

    @app.get("/crash")
    async def crash() -> None:
        raise RuntimeError("internal details that must not leak")

    @app.get("/typed")
    async def typed(page: int) -> dict[str, int]:
        return {"page": page}

    return app


@pytest.fixture
async def errors_client(errors_app: FastAPI) -> AsyncIterator[AsyncClient]:
    # Starlette re-raises unhandled errors after responding; we only care about the response.
    transport = ASGITransport(app=errors_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def protected_client_app(container: Container) -> FastAPI:
    """App with a single protected route; `container` wires `require_auth` to test settings."""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/protected")
    async def protected(client_id: str = Depends(require_auth)) -> dict[str, str]:
        return {"client_id": client_id}

    return app


@pytest.fixture
async def protected_client(protected_client_app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=protected_client_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


_STORED_AT = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)


def _stored(index: int, **overrides: object) -> Podcast:
    """A podcast as it comes back from the repository, with deterministic identity."""
    return PodcastFactory.build(
        id=UUID(int=index),
        ref=ExternalRef("itunes", str(index)),
        created_at=_STORED_AT,
        updated_at=_STORED_AT,
        **overrides,
    )


@pytest.fixture
def stored_podcasts() -> list[Podcast]:
    return [
        _stored(1),
        _stored(
            2,
            title='=HYPERLINK("http://evil.test")',
            author="-Spreadsheet, Injection",
            description=None,
            palette=None,
            genres=("=1+1", "Music", "Rock, Punk"),
        ),
    ]


@pytest.fixture
def many_stored_podcasts() -> list[Podcast]:
    return [_stored(index) for index in range(450)]


@pytest.fixture
def observed_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.add_middleware(RequestContextMiddleware)

    @app.get("/items/{item_id}")
    async def item(item_id: int) -> dict[str, object]:
        return {"item_id": item_id, "request_id": request_id_var.get()}

    @app.get("/crash")
    async def crash() -> None:
        raise RuntimeError("bug")

    return app


@pytest.fixture
async def observed_client(observed_app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=observed_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
