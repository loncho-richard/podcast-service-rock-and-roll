import httpx
from dependency_injector import containers, providers

from podcast_service.application.auth import IssueAccessToken
from podcast_service.application.ingestion import (
    BulkIngestPodcasts,
    IngestSinglePodcast,
    PodcastEnricher,
)
from podcast_service.application.podcast import ExportPodcasts, GetPodcast, ListPodcasts
from podcast_service.config import Settings
from podcast_service.domain.ingestion import PodcastNormalizer, RockRelevancePolicy
from podcast_service.infrastructure import RateLimiter, RetryPolicy
from podcast_service.infrastructure.auth import JwtTokenService
from podcast_service.infrastructure.feeds import RssFeedReader
from podcast_service.infrastructure.imaging import HttpImageFetcher, PillowPaletteExtractor
from podcast_service.infrastructure.persistence import (
    DatabaseHealthProbe,
    SqlAlchemyUnitOfWork,
    create_engine,
    create_session_factory,
)
from podcast_service.infrastructure.sources.itunes import ITunesPodcastSource, ITunesSampleFallback


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
        rate_limiter=providers.Singleton(
            RateLimiter,
            name="itunes",
            max_calls=settings.provided.itunes_rate_limit_calls,
            period=settings.provided.itunes_rate_limit_period_seconds,
            max_wait=settings.provided.itunes_rate_limit_max_wait_seconds,
        ),
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
            deadline_seconds=settings.provided.download_deadline_seconds,
        ),
        image_fetcher=providers.Singleton(
            HttpImageFetcher,
            http_client=http_client,
            retry_policy=enrichment_retry_policy,
            max_bytes=settings.provided.max_cover_bytes,
            deadline_seconds=settings.provided.download_deadline_seconds,
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

    # --- queries ---
    list_podcasts = providers.Factory(ListPodcasts, uow_factory=unit_of_work.provider)
    get_podcast = providers.Factory(GetPodcast, uow_factory=unit_of_work.provider)
    export_podcasts = providers.Factory(ExportPodcasts, uow_factory=unit_of_work.provider)
