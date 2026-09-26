import pytest
from httpx import AsyncClient
from syrupy.assertion import SnapshotAssertion


@pytest.mark.parametrize(
    "path",
    ["/not-found", "/domain-error", "/crash", "/typed?page=abc", "/unknown-route"],
)
async def test_every_error_uses_the_shared_json_shape(
    errors_client: AsyncClient, snapshot: SnapshotAssertion, path: str
) -> None:
    response = await errors_client.get(path)

    assert {"status_code": response.status_code, "body": response.json()} == snapshot
