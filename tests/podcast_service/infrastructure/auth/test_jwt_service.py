import pytest

from podcast_service.application.auth.errors import AuthenticationError
from podcast_service.infrastructure.auth.jwt_service import JwtTokenService


def test_issued_token_verifies_back_to_its_subject(token_service: JwtTokenService) -> None:
    token = token_service.issue(subject="test-client")

    assert (token.expires_in, token_service.verify(token.token)) == (3600, "test-client")


def test_expired_token_is_rejected(
    token_service: JwtTokenService, token_service_two_hours_ago: JwtTokenService
) -> None:
    token = token_service_two_hours_ago.issue(subject="test-client")

    with pytest.raises(AuthenticationError, match="expired"):
        token_service.verify(token.token)


def test_valid_forged_token_is_accepted(
    token_service: JwtTokenService, forged_tokens: dict[str, str]
) -> None:
    assert token_service.verify(forged_tokens["valid"]) == "test-client"


@pytest.mark.parametrize(
    "scenario",
    ["expired", "wrong-signature", "wrong-issuer", "missing-subject", "alg-none", "garbage"],
)
def test_untrustworthy_tokens_are_rejected(
    token_service: JwtTokenService, forged_tokens: dict[str, str], scenario: str
) -> None:
    with pytest.raises(AuthenticationError):
        token_service.verify(forged_tokens[scenario])
