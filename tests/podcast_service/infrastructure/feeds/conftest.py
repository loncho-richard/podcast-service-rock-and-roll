import httpx
import pytest

from fakes import ChunkedBody
from podcast_service.infrastructure import RetryPolicy
from podcast_service.infrastructure.feeds import RssFeedReader


@pytest.fixture
def rss_reader(http_client: httpx.AsyncClient, retry_policy: RetryPolicy) -> RssFeedReader:
    return RssFeedReader(http_client, retry_policy, max_bytes=10_000, deadline_seconds=5)


@pytest.fixture
def rss_feed() -> bytes:
    """Channel header first, then (many) episodes, like real podcast feeds."""
    episodes = "".join(
        f"<item><title>Episode {n}</title><description>{'x' * 200}</description></item>"
        for n in range(200)
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>Classic Rock Hour</title>
    <language>en-us</language>
    <description>Short description.</description>
    <itunes:summary>
      <![CDATA[<p>Stories behind the <b>greatest</b> rock records.</p>]]>
    </itunes:summary>
    {episodes}
  </channel>
</rss>""".encode()


@pytest.fixture
def rss_feed_without_summary() -> bytes:
    return b"""<?xml version="1.0"?>
<rss version="2.0"><channel>
  <title>Punk Tapes</title><description>Only a description.</description>
</channel></rss>"""


@pytest.fixture
def streamed_feed() -> ChunkedBody:
    """Header in the first two chunks, then 501 episodes."""
    return ChunkedBody(
        b'<?xml version="1.0"?><rss version="2.0"><channel><title>Punk Tapes</title>',
        b"<language>en-gb</language><description>Garage punk.</description>",
        b"<item><title>Episode 1</title></item>",
        *(b"<item><title>Older episode</title></item>" for _ in range(500)),
    )
