import httpx
from dependency_injector import containers, providers

from podcast_service.application.auth.issue_token import IssueAccessToken
from podcast_service.application.ingestion.bulk_ingest import BulkIngestPodcasts
from podcast_service.application.ingestion.enrichment import PodcastEnricher
from podcast_service.application.ingestion.single_ingest import IngestSinglePodcast
from podcast_service.config import Settings
from podcast_service.domain.ingestion.normalizer import PodcastNormalizer
from podcast_service.domain.ingestion.relevance import RockRelevancePolicy
from podcast_service.infrastructure.auth.jwt_service import JwtTokenService
from podcast_service.infrastructure.feeds.rss_reader import RssFeedReader
from podcast_service.infrastructure.imaging.http_image_fetcher import HttpImageFetcher
from podcast_service.infrastructure.imaging.pillow_palette_extractor import (
    PillowPaletteExtractor,
)
from podcast_service.infrastructure.persistence.database import (
    DatabaseHealthProbe,
    create_engine,
    create_session_factory,
)
from podcast_service.infrastructure.persistence.unit_of_work import SqlAlchemyUnitOfWork
from podcast_service.infrastructure.resilience import RetryPolicy
from podcast_service.infrastructure.sources.itunes.client import ITunesPodcastSource
from podcast_service.infrastructure.sources.itunes.fallback import ITunesSampleFallback


class Container(containers.DeclarativeContainer):
    """Composition root: the only place where concrete implementations are chosen."""

    wiring_config = containers.WiringConfiguration(
        packages=["podcast_service.api.routers"],
        modules=["podcast_service.api.security"],
    )

    settings = providers.Singleton(Settings)

    # --- persistence ---
    engine = providers.Singleton(create_engine, database_url=settings.provided.database_url)
    session_factory = providers.Singleton(create_session_factory, engine=engine)
    unit_of_work = providers.Factory(SqlAlchemyUnitOfWork, session_factory=session_factory)
    database_health_probe = providers.Factory(DatabaseHealthProbe, engine=engine)

    # --- auth ---
    token_service = providers.Singleton(
        JwtTokenService,
        secret=settings.provided.jwt_secret.get_secret_value.call(),
        issuer=settings.provided.jwt_issuer,
        ttl_seconds=settings.provided.jwt_ttl_seconds,
    )
    issue_access_token = providers.Factory(
        IssueAccessToken,
        client_id=settings.provided.auth_client_id,
        client_secret=settings.provided.auth_client_secret.get_secret_value.call(),
        token_service=token_service,
    )

    # --- outbound HTTP ---
    http_client = providers.Singleton(
        httpx.AsyncClient,
        timeout=settings.provided.http_timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": "rock-podcast-service/0.1"},
    )
    retry_policy = providers.Singleton(
        RetryPolicy,
        attempts=settings.provided.http_retry_attempts,
        max_delay=settings.provided.http_retry_max_delay_seconds,
    )

    # --- ingestion ---
    podcast_source = providers.Singleton(
        ITunesPodcastSource,
        http_client=http_client,
        base_url=settings.provided.itunes_base_url,
        country=settings.provided.itunes_country,
        retry_policy=retry_policy,
        fallback=providers.Singleton(ITunesSampleFallback),
    )
    normalizer = providers.Singleton(
        PodcastNormalizer, relevance=providers.Singleton(RockRelevancePolicy)
    )

    # Enrichment is best effort: fewer retries than the primary source.
    enrichment_retry_policy = providers.Singleton(
        RetryPolicy,
        attempts=settings.provided.enrichment_retry_attempts,
        max_delay=settings.provided.http_retry_max_delay_seconds,
    )
    enricher = providers.Singleton(
        PodcastEnricher,
        feed_reader=providers.Singleton(
            RssFeedReader,
            http_client=http_client,
            retry_policy=enrichment_retry_policy,
            max_bytes=settings.provided.max_feed_bytes,
        ),
        image_fetcher=providers.Singleton(
            HttpImageFetcher,
            http_client=http_client,
            retry_policy=enrichment_retry_policy,
            max_bytes=settings.provided.max_cover_bytes,
        ),
        palette_extractor=providers.Singleton(
            PillowPaletteExtractor, colors=settings.provided.palette_size
        ),
        normalizer=normalizer,
        max_concurrency=settings.provided.enrichment_concurrency,
    )

    bulk_ingest = providers.Factory(
        BulkIngestPodcasts,
        source=podcast_source,
        normalizer=normalizer,
        enricher=enricher,
        uow_factory=unit_of_work.provider,
        default_terms=settings.provided.itunes_search_terms,
    )
    ingest_single = providers.Factory(
        IngestSinglePodcast,
        source=podcast_source,
        normalizer=normalizer,
        enricher=enricher,
        uow_factory=unit_of_work.provider,
    )
