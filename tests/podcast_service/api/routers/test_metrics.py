from httpx import AsyncClient


async def test_metrics_are_public_in_prometheus_format(client: AsyncClient) -> None:
    await client.get("/health")

    response = await client.get("/metrics")

    assert (
        response.status_code,
        response.headers["content-type"].split(";")[0],
        'http_requests_total{method="GET",route="/health"' in response.text,
    ) == (200, "text/plain", True)
