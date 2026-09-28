import asyncio
import logging
from typing import Any

import feedparser
import httpx

from podcast_service.domain.ingestion import FeedDetails, FeedReader
from podcast_service.infrastructure import RetryPolicy, download
from podcast_service.infrastructure.observability import record_upstream

logger = logging.getLogger(__name__)


class RssFeedReader(FeedReader):
    """Reads channel-level details (description, language) from a podcast RSS feed.

    Only the channel header is needed, and it comes first in the document, so the
    download is capped: huge feeds with thousands of episodes are simply truncated
    and feedparser (which is lenient with broken XML) still reads the header.
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        retry_policy: RetryPolicy,
        max_bytes: int,
        deadline_seconds: float,
    ) -> None:
        self._http = http_client
        self._retry_policy = retry_policy
        self._max_bytes = max_bytes
        self._deadline_seconds = deadline_seconds

    async def read(self, feed_url: str) -> FeedDetails | None:
        try:
            body = await download(
                self._http, feed_url, self._retry_policy, self._max_bytes, self._deadline_seconds
            )
            parsed: Any = await asyncio.to_thread(feedparser.parse, body.content)
        except Exception as exc:  # enrichment must never break an ingestion
            record_upstream("feed", succeeded=False)
            logger.warning("Could not read feed %s: %r", feed_url, exc)
            return None

        if not parsed.get("version"):  # e.g. an HTML error page served with a 200
            record_upstream("feed", succeeded=False)
            logger.warning("%s is not an RSS/Atom feed", feed_url)
            return None
        record_upstream("feed", succeeded=True)
        channel = parsed.get("feed") or {}
        details = FeedDetails(
            # itunes:summary is usually the long form; <description> is the fallback.
            description=_text(channel.get("summary")) or _text(channel.get("subtitle")),
            language=_text(channel.get("language")),
        )
        if details == FeedDetails():
            logger.warning("Feed %s has no usable channel details", feed_url)
            return None
        return details


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None
