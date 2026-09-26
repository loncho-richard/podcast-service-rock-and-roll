import pytest
from pydantic import ValidationError

from podcast_service.config import Settings


@pytest.mark.parametrize(
    "overrides",
    [
        {"jwt_secret": "too-short"},
        {"auth_client_secret": "short"},
        {"auth_client_id": ""},
    ],
    ids=["short-jwt-secret", "short-client-secret", "empty-client-id"],
)
def test_weak_auth_settings_are_refused_at_startup(
    settings: Settings, overrides: dict[str, str]
) -> None:
    values = {
        "auth_client_id": settings.auth_client_id,
        "auth_client_secret": settings.auth_client_secret.get_secret_value(),
        "jwt_secret": settings.jwt_secret.get_secret_value(),
    }

    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{**values, **overrides})  # type: ignore[call-arg, arg-type]
