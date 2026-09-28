import asyncio

import httpx
import pytest
import respx

from fakes import ChunkedBody
from podcast_service.infrastructure import Download, RetryPolicy, download

URL = "https://files.test/cover.jpg"


async def test_download_returns_body_and_content_type(
    respx_mock: respx.MockRouter, http_client: httpx.AsyncClient, retry_policy: RetryPolicy
) -> None:
    respx_mock.get(URL).mock(
        return_value=httpx.Response(200, content=b"12345", headers={"Content-Type": "image/jpeg"})
    )

    result = await download(http_client, URL, retry_policy, max_bytes=10, deadline_seconds=5)

    assert result == Download(content=b"12345", content_type="image/jpeg", truncated=False)


async def test_download_stops_reading_at_the_cap(
    respx_mock: respx.MockRouter, http_client: httpx.AsyncClient, retry_policy: RetryPolicy
) -> None:
    respx_mock.get(URL).mock(return_value=httpx.Response(200, content=b"x" * 100))

    result = await download(http_client, URL, retry_policy, max_bytes=10, deadline_seconds=5)

    assert (result.content, result.truncated) == (b"x" * 10, True)


async def test_download_retries_transient_failures(
    respx_mock: respx.MockRouter, http_client: httpx.AsyncClient, retry_policy: RetryPolicy
) -> None:
    route = respx_mock.get(URL).mock(
        side_effect=[httpx.Response(502), httpx.Response(200, content=b"ok")]
    )

    result = await download(http_client, URL, retry_policy, max_bytes=10, deadline_seconds=5)

    assert (result.content, route.call_count) == (b"ok", 2)


async def _trickle(request: httpx.Request) -> httpx.Response:
    await asyncio.sleep(1)  # a server that keeps the connection alive but never finishes
    return httpx.Response(200, content=b"late")


async def test_download_gives_up_at_the_deadline(
    respx_mock: respx.MockRouter, http_client: httpx.AsyncClient, retry_policy: RetryPolicy
) -> None:
    respx_mock.get(URL).mock(side_effect=_trickle)

    with pytest.raises(TimeoutError):
        await download(http_client, URL, retry_policy, max_bytes=10, deadline_seconds=0.05)


@pytest.mark.parametrize(
    "chunks",
    [
        (b"<rss><channel>", b"<title>x</title><item>1</item>", b"<item>2</item>", b"..."),
        (b"<rss><channel><title>x</title><it", b"em>1</item>", b"<item>2</item>", b"..."),
    ],
    ids=["marker-in-a-chunk", "marker-split-across-chunks"],
)
async def test_download_stops_reading_once_a_marker_arrives(
    respx_mock: respx.MockRouter,
    http_client: httpx.AsyncClient,
    retry_policy: RetryPolicy,
    chunks: tuple[bytes, ...],
) -> None:
    body = ChunkedBody(*chunks)
    respx_mock.get(URL).mock(return_value=httpx.Response(200, content=body))

    result = await download(
        http_client, URL, retry_policy, max_bytes=1_000, deadline_seconds=5, stop_at=(b"<item",)
    )

    assert (body.served, result.content) == (2, b"".join(chunks[:2]))
