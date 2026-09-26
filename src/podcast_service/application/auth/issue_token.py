from secrets import compare_digest

from podcast_service.application.auth.errors import AuthenticationError
from podcast_service.application.auth.ports import AccessToken, TokenService


class IssueAccessToken:
    """Exchange the static client credentials for a short-lived access token."""

    def __init__(self, client_id: str, client_secret: str, token_service: TokenService) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_service = token_service

    def execute(self, client_id: str, client_secret: str) -> AccessToken:
        # Constant-time comparisons, both always evaluated, so timing leaks nothing.
        id_matches = compare_digest(client_id.encode(), self._client_id.encode())
        secret_matches = compare_digest(client_secret.encode(), self._client_secret.encode())
        if not (id_matches & secret_matches):
            raise AuthenticationError("Invalid client credentials.")
        return self._token_service.issue(subject=client_id)
