from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from podcast_service.api.errors import register_exception_handlers
from podcast_service.api.middleware import RequestContextMiddleware
from podcast_service.api.routers import auth, health, ingestion, metrics, podcasts
from podcast_service.container import Container
from podcast_service.infrastructure.observability import configure_logging


def create_app(container: Container | None = None) -> FastAPI:
    """Application factory. Tests pass their own container to override providers."""
    container = container or Container()
    settings = container.settings()
    configure_logging(settings.log_level, settings.log_format)

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
    register_exception_handlers(app)
    app.add_middleware(RequestContextMiddleware)
    app.include_router(health.router)
    app.include_router(metrics.router)
    app.include_router(auth.router)
    app.include_router(ingestion.router)
    app.include_router(podcasts.router)
    return app
