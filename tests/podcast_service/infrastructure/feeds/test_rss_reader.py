from collections.abc import Callable

import httpx
import pytest
import respx

from podcast_service.domain.ingestion.ports import FeedDetails
from podcast_service.infrastructure.feeds.rss_reader import RssFeedReader

FEED_URL = "https://feeds.test/rock.xml"


def _unreachable(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("unreachable", request=request)


async def test_reads_summary_and_language_from_a_large_truncated_feed(
    respx_mock: respx.MockRouter, rss_reader: RssFeedReader, rss_feed: bytes
) -> None:
    assert len(rss_feed) > 10_000  # larger than the reader's cap
    respx_mock.get(FEED_URL).mock(return_value=httpx.Response(200, content=rss_feed))

    details = await rss_reader.read(FEED_URL)

    assert details == FeedDetails(
        description="<p>Stories behind the <b>greatest</b> rock records.</p>",
        language="en-us",
    )


async def test_falls_back_to_the_channel_description(
    respx_mock: respx.MockRouter, rss_reader: RssFeedReader, rss_feed_without_summary: bytes
) -> None:
    respx_mock.get(FEED_URL).mock(
        return_value=httpx.Response(200, content=rss_feed_without_summary)
    )

    assert await rss_reader.read(FEED_URL) == FeedDetails(description="Only a description.")


@pytest.mark.parametrize(
    "respond",
    [
        lambda _: httpx.Response(404),
        lambda _: httpx.Response(503),
        _unreachable,
        lambda _: httpx.Response(200, content=b"<html><body>Not a feed</body></html>"),
        lambda _: httpx.Response(200, content=b"\x00\x01 binary garbage"),
    ],
    ids=["not-found", "server-error", "unreachable", "html-page", "garbage"],
)
async def test_unusable_feeds_return_none(
    respx_mock: respx.MockRouter,
    rss_reader: RssFeedReader,
    respond: Callable[[httpx.Request], httpx.Response],
) -> None:
    respx_mock.get(FEED_URL).mock(side_effect=respond)

    assert await rss_reader.read(FEED_URL) is None
