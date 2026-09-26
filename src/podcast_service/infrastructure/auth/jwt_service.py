from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import jwt

from podcast_service.application.auth.errors import AuthenticationError
from podcast_service.application.auth.ports import AccessToken, TokenService

# Pinned: the algorithm is never taken from the token header (prevents alg=none / confusion).
_ALGORITHM = "HS256"
_REQUIRED_CLAIMS = ["exp", "iat", "iss", "sub"]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class JwtTokenService(TokenService):
    def __init__(
        self,
        secret: str,
        issuer: str,
        ttl_seconds: int,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._secret = secret
        self._issuer = issuer
        self._ttl_seconds = ttl_seconds
        self._clock = clock

    def issue(self, subject: str) -> AccessToken:
        now = self._clock()
        claims = {
            "sub": subject,
            "iss": self._issuer,
            "iat": now,
            "exp": now + timedelta(seconds=self._ttl_seconds),
        }
        token = jwt.encode(claims, self._secret, algorithm=_ALGORITHM)
        return AccessToken(token=token, expires_in=self._ttl_seconds)

    def verify(self, token: str) -> str:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[_ALGORITHM],
                issuer=self._issuer,
                options={"require": _REQUIRED_CLAIMS},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Access token has expired.") from exc
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("Invalid access token.") from exc
        return str(claims["sub"])
