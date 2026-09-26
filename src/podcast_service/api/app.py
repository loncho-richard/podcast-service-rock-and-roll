import logging

from fastapi import FastAPI

from podcast_service.api.errors import register_exception_handlers
from podcast_service.api.routers import health
from podcast_service.container import Container


def create_app(container: Container | None = None) -> FastAPI:
    """Application factory. Tests pass their own container to override providers."""
    container = container or Container()
    settings = container.settings()
    logging.basicConfig(level=settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Catalog of rock & roll podcasts: ingestion, search and export.",
    )
    app.state.container = container
    register_exception_handlers(app)
    app.include_router(health.router)
    return app
