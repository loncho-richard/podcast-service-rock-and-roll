from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Kept separate so migrations can run without the API's secrets."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://podcasts:podcasts@localhost:5432/podcasts"


class Settings(DatabaseSettings):
    """Application settings, read from environment variables (or a local `.env`)."""

    app_name: str = "Rock & Roll Podcast Service"
    log_level: str = "INFO"

    # Single static client (the brief rules out user management). No defaults on
    # purpose: the service refuses to start with a well-known secret.
    auth_client_id: str = Field(min_length=1)
    auth_client_secret: SecretStr = Field(min_length=12)
    jwt_secret: SecretStr = Field(min_length=32)
    jwt_issuer: str = "podcast-service"
    jwt_ttl_seconds: int = Field(default=3600, gt=0)

    # Outbound HTTP (iTunes, RSS feeds, cover images).
    http_timeout_seconds: float = Field(default=10.0, gt=0)
    http_retry_attempts: int = Field(default=3, ge=1)
    http_retry_max_delay_seconds: float = Field(default=8.0, ge=0)

    itunes_base_url: str = "https://itunes.apple.com"
    itunes_country: str = "US"
    # Used by bulk ingestion when the request does not name its own terms.
    itunes_search_terms: list[str] = [
        "rock and roll",
        "classic rock",
        "punk rock",
        "hard rock",
        "heavy metal",
        "rockabilly",
    ]

    # Enrichment (RSS details + cover palette), all best effort.
    enrichment_concurrency: int = Field(default=8, ge=1)
    enrichment_retry_attempts: int = Field(default=2, ge=1)
    max_feed_bytes: int = Field(default=2_000_000, gt=0)
    max_cover_bytes: int = Field(default=5_000_000, gt=0)
    palette_size: int = Field(default=5, ge=1, le=16)
