import logging

import httpx

from podcast_service.domain.ingestion.ports import ImageFetcher
from podcast_service.infrastructure.http import download
from podcast_service.infrastructure.resilience import RetryPolicy

logger = logging.getLogger(__name__)


class HttpImageFetcher(ImageFetcher):
    """Downloads cover images, refusing non-images and anything above `max_bytes`."""

    def __init__(
        self, http_client: httpx.AsyncClient, retry_policy: RetryPolicy, max_bytes: int
    ) -> None:
        self._http = http_client
        self._retry_policy = retry_policy
        self._max_bytes = max_bytes

    async def fetch(self, url: str) -> bytes | None:
        try:
            body = await download(self._http, url, self._retry_policy, self._max_bytes)
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            logger.warning("Could not download cover %s: %r", url, exc)
            return None
        if not body.content_type.startswith("image/"):
            logger.warning("Cover %s is not an image (%s)", url, body.content_type)
            return None
        if body.truncated:
            logger.warning("Cover %s exceeds %d bytes", url, self._max_bytes)
            return None
        return body.content
