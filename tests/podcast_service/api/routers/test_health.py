import pytest
from httpx import AsyncClient


@pytest.mark.usefixtures("live_database")
async def test_health_reports_ok_when_the_database_is_reachable(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert (response.status_code, response.json()) == (200, {"status": "ok", "database": "ok"})


async def test_health_reports_degraded_when_the_database_is_down(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert (response.status_code, response.json()) == (
        503,
        {"status": "degraded", "database": "unavailable"},
    )
