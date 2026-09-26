import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from podcast_service.api.errors import register_exception_handlers
from podcast_service.api.routers import auth, health, ingestion
from podcast_service.container import Container


def create_app(container: Container | None = None) -> FastAPI:
    """Application factory. Tests pass their own container to override providers."""
    container = container or Container()
    settings = container.settings()
    logging.basicConfig(level=settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await container.http_client().aclose()
        await container.engine().dispose()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Catalog of rock & roll podcasts: ingestion, search and export.",
        lifespan=lifespan,
    )
    app.state.container = container
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(ingestion.router)
    return app
