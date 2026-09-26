import pytest

from podcast_service.application.auth import AccessToken, IssueAccessToken, TokenService


class FakeTokenService(TokenService):
    def issue(self, subject: str) -> AccessToken:
        return AccessToken(token=f"token-for-{subject}", expires_in=60)

    def verify(self, token: str) -> str:
        return token.removeprefix("token-for-")


@pytest.fixture
def issue_access_token() -> IssueAccessToken:
    return IssueAccessToken(
        client_id="test-client",
        client_secret="test-client-secret",
        token_service=FakeTokenService(),
    )
