"""One router per resource; wired to the DI container by package."""

from podcast_service.api.routers import auth, health, ingestion, metrics, podcasts

__all__ = ["auth", "health", "ingestion", "metrics", "podcasts"]
