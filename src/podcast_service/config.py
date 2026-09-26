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
