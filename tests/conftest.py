from collections.abc import AsyncIterator, Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from prometheus_client import REGISTRY
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.community.postgres import PostgresContainer

from fakes import (
    FEED_URL,
    FakeFeedReader,
    FakeImageFetcher,
    FakePaletteExtractor,
    FakePodcastSource,
    upstream_records,
)
from podcast_service.api.app import create_app
from podcast_service.application.ingestion import PodcastEnricher
from podcast_service.config import Settings
from podcast_service.container import Container
from podcast_service.domain.ingestion import FeedDetails, PodcastNormalizer, RockRelevancePolicy
from podcast_service.infrastructure.persistence import create_engine

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
    return Settings(  # type: ignore[call-arg]
        _env_file=None,
        database_url=_UNREACHABLE_DATABASE_URL,
        auth_client_id="test-client",
        auth_client_secret="test-client-secret",
        jwt_secret="test-jwt-secret-that-is-long-enough-0123456789",
    )


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


# --- metrics -------------------------------------------------------------------


@pytest.fixture
def metric_delta() -> Callable[..., Callable[[], float]]:
    """Metrics are process-wide, so tests measure the increase since `track(...)`."""

    def track(name: str, **labels: str) -> Callable[[], float]:
        before = REGISTRY.get_sample_value(name, labels) or 0.0
        return lambda: (REGISTRY.get_sample_value(name, labels) or 0.0) - before

    return track


# --- auth --------------------------------------------------------------------


@pytest.fixture
def auth_headers(container: Container) -> dict[str, str]:
    token = container.token_service().issue(subject="test-client").token
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def forged_tokens(settings: Settings) -> dict[str, str]:
    """Hand-made tokens, one per scenario the verifier must accept or reject."""
    secret = settings.jwt_secret.get_secret_value()
    now = datetime.now(UTC)
    claims = {
        "sub": "test-client",
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    without_subject = {key: value for key, value in claims.items() if key != "sub"}
    expired = {**claims, "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)}
    return {
        "valid": jwt.encode(claims, secret, algorithm="HS256"),
        "expired": jwt.encode(expired, secret, algorithm="HS256"),
        "wrong-signature": jwt.encode(claims, "x" * 48, algorithm="HS256"),
        "wrong-issuer": jwt.encode({**claims, "iss": "someone-else"}, secret, algorithm="HS256"),
        "missing-subject": jwt.encode(without_subject, secret, algorithm="HS256"),
        "alg-none": jwt.encode(claims, None, algorithm="none"),
        "garbage": "not-a-jwt",
    }


# --- ingestion fakes (no network) ---------------------------------------------


@pytest.fixture
def normalizer() -> PodcastNormalizer:
    return PodcastNormalizer(RockRelevancePolicy())


@pytest.fixture
def feed_reader() -> FakeFeedReader:
    return FakeFeedReader(
        {FEED_URL: FeedDetails(description="<p>From the <b>feed</b></p>", language="en-gb")}
    )


@pytest.fixture
def enricher(feed_reader: FakeFeedReader, normalizer: PodcastNormalizer) -> PodcastEnricher:
    return PodcastEnricher(
        feed_reader=feed_reader,
        image_fetcher=FakeImageFetcher(),
        palette_extractor=FakePaletteExtractor(),
        normalizer=normalizer,
        max_concurrency=3,
    )


@pytest.fixture
def fake_source() -> FakePodcastSource:
    return FakePodcastSource(upstream_records())


@pytest.fixture
def fake_upstream(
    container: Container, fake_source: FakePodcastSource, enricher: PodcastEnricher
) -> FakePodcastSource:
    """Replace iTunes, RSS feeds and cover downloads with in-memory fakes."""
    container.podcast_source.override(fake_source)
    container.enricher.override(enricher)
    return fake_source


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
