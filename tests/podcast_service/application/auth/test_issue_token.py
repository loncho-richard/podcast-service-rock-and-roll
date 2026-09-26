import pytest

from podcast_service.application.auth import AccessToken, AuthenticationError, IssueAccessToken


def test_valid_credentials_get_a_token(issue_access_token: IssueAccessToken) -> None:
    token = issue_access_token.execute("test-client", "test-client-secret")

    assert token == AccessToken(token="token-for-test-client", expires_in=60)


@pytest.mark.parametrize(
    ("client_id", "client_secret"),
    [
        ("test-client", "wrong-secret"),
        ("other-client", "test-client-secret"),
        ("", ""),
    ],
    ids=["wrong-secret", "wrong-client", "empty"],
)
def test_invalid_credentials_are_rejected(
    issue_access_token: IssueAccessToken, client_id: str, client_secret: str
) -> None:
    with pytest.raises(AuthenticationError):
        issue_access_token.execute(client_id, client_secret)
