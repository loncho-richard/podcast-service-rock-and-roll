from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from podcast_service.api.errors import register_exception_handlers
from podcast_service.domain.shared.exceptions import DomainError, NotFoundError


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
