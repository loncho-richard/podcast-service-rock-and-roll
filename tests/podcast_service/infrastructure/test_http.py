import httpx
import respx

from podcast_service.infrastructure.http import Download, download
from podcast_service.infrastructure.resilience import RetryPolicy

URL = "https://files.test/cover.jpg"


async def test_download_returns_body_and_content_type(
    respx_mock: respx.MockRouter, http_client: httpx.AsyncClient, retry_policy: RetryPolicy
) -> None:
    respx_mock.get(URL).mock(
        return_value=httpx.Response(200, content=b"12345", headers={"Content-Type": "image/jpeg"})
    )

    result = await download(http_client, URL, retry_policy, max_bytes=10)

    assert result == Download(content=b"12345", content_type="image/jpeg", truncated=False)


async def test_download_stops_reading_at_the_cap(
    respx_mock: respx.MockRouter, http_client: httpx.AsyncClient, retry_policy: RetryPolicy
) -> None:
    respx_mock.get(URL).mock(return_value=httpx.Response(200, content=b"x" * 100))

    result = await download(http_client, URL, retry_policy, max_bytes=10)

    assert (result.content, result.truncated) == (b"x" * 10, True)


async def test_download_retries_transient_failures(
    respx_mock: respx.MockRouter, http_client: httpx.AsyncClient, retry_policy: RetryPolicy
) -> None:
    route = respx_mock.get(URL).mock(
        side_effect=[httpx.Response(502), httpx.Response(200, content=b"ok")]
    )

    result = await download(http_client, URL, retry_policy, max_bytes=10)

    assert (result.content, route.call_count) == (b"ok", 2)
