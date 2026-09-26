import pytest
from httpx import AsyncClient
from syrupy.assertion import SnapshotAssertion

from podcast_service.container import Container


async def test_valid_credentials_return_a_usable_bearer_token(
    client: AsyncClient, container: Container
) -> None:
    response = await client.post(
        "/auth/token", data={"username": "test-client", "password": "test-client-secret"}
    )

    body = response.json()
    assert (
        response.status_code,
        body["token_type"],
        body["expires_in"],
        container.token_service().verify(body["access_token"]),
    ) == (200, "bearer", 3600, "test-client")


@pytest.mark.parametrize(
    "form",
    [
        {"username": "test-client", "password": "wrong-secret"},
        {"username": "someone-else", "password": "test-client-secret"},
        {"username": "test-client"},
    ],
    ids=["wrong-secret", "wrong-client", "missing-password"],
)
async def test_bad_credentials_are_rejected(
    client: AsyncClient, snapshot: SnapshotAssertion, form: dict[str, str]
) -> None:
    response = await client.post("/auth/token", data=form)

    assert {"status_code": response.status_code, "body": response.json()} == snapshot
