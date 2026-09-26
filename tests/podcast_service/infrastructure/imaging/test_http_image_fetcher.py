import httpx
import pytest
import respx

from podcast_service.infrastructure.imaging.http_image_fetcher import HttpImageFetcher

COVER_URL = "https://images.test/cover.png"


async def test_fetches_image_bytes(
    respx_mock: respx.MockRouter, image_fetcher: HttpImageFetcher
) -> None:
    respx_mock.get(COVER_URL).mock(
        return_value=httpx.Response(
            200, content=b"png-bytes", headers={"Content-Type": "image/png"}
        )
    )

    assert await image_fetcher.fetch(COVER_URL) == b"png-bytes"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(404),
        httpx.Response(503),
        httpx.Response(200, content=b"<html/>", headers={"Content-Type": "text/html"}),
        httpx.Response(200, content=b"x" * 2_000, headers={"Content-Type": "image/jpeg"}),
    ],
    ids=["not-found", "server-error", "not-an-image", "too-large"],
)
async def test_unusable_covers_return_none(
    respx_mock: respx.MockRouter, image_fetcher: HttpImageFetcher, response: httpx.Response
) -> None:
    respx_mock.get(COVER_URL).mock(return_value=response)

    assert await image_fetcher.fetch(COVER_URL) is None


async def test_malformed_url_returns_none(image_fetcher: HttpImageFetcher) -> None:
    assert await image_fetcher.fetch("https://") is None
