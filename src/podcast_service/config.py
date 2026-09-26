from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, read from environment variables (or a local `.env`)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Rock & Roll Podcast Service"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://podcasts:podcasts@localhost:5432/podcasts"
