from datetime import UTC, datetime, timedelta

import pytest

from podcast_service.config import Settings
from podcast_service.infrastructure.auth.jwt_service import JwtTokenService


@pytest.fixture
def token_service(settings: Settings) -> JwtTokenService:
    return JwtTokenService(
        secret=settings.jwt_secret.get_secret_value(),
        issuer=settings.jwt_issuer,
        ttl_seconds=3600,
    )


@pytest.fixture
def token_service_two_hours_ago(settings: Settings) -> JwtTokenService:
    """Issues tokens as if it were two hours ago, so a 1h token is already expired."""
    return JwtTokenService(
        secret=settings.jwt_secret.get_secret_value(),
        issuer=settings.jwt_issuer,
        ttl_seconds=3600,
        clock=lambda: datetime.now(UTC) - timedelta(hours=2),
    )
