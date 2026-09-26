from dependency_injector.wiring import Provide, inject
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from podcast_service.application.auth import AuthenticationError, TokenService
from podcast_service.container import Container

# OAuth2 password flow so the "Authorize" button in /docs can fetch a token directly.
_bearer = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


@inject
async def require_auth(
    token: str | None = Depends(_bearer),
    token_service: TokenService = Depends(Provide[Container.token_service]),
) -> str:
    """Protect a route; returns the authenticated client id."""
    if token is None:
        raise AuthenticationError("Missing bearer token.")
    return token_service.verify(token)
