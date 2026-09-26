from httpx import AsyncClient


async def test_health_is_public_and_reports_ok(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert (response.status_code, response.json()) == (200, {"status": "ok"})
