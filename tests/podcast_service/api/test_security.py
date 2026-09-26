import pytest
from httpx import AsyncClient
from syrupy.assertion import SnapshotAssertion


async def test_valid_token_grants_access(
    protected_client: AsyncClient, forged_tokens: dict[str, str]
) -> None:
    response = await protected_client.get(
        "/protected", headers={"Authorization": f"Bearer {forged_tokens['valid']}"}
    )

    assert (response.status_code, response.json()) == (200, {"client_id": "test-client"})


async def test_missing_token_is_rejected(
    protected_client: AsyncClient, snapshot: SnapshotAssertion
) -> None:
    response = await protected_client.get("/protected")

    assert {
        "status_code": response.status_code,
        "www_authenticate": response.headers.get("www-authenticate"),
        "body": response.json(),
    } == snapshot


@pytest.mark.parametrize(
    "scenario",
    ["expired", "wrong-signature", "wrong-issuer", "missing-subject", "alg-none", "garbage"],
)
async def test_untrustworthy_token_is_rejected(
    protected_client: AsyncClient,
    forged_tokens: dict[str, str],
    snapshot: SnapshotAssertion,
    scenario: str,
) -> None:
    response = await protected_client.get(
        "/protected", headers={"Authorization": f"Bearer {forged_tokens[scenario]}"}
    )

    assert {
        "status_code": response.status_code,
        "www_authenticate": response.headers.get("www-authenticate"),
        "body": response.json(),
    } == snapshot
