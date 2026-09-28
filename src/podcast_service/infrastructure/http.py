import asyncio
from dataclasses import dataclass

import httpx

from podcast_service.infrastructure.resilience import RetryPolicy


@dataclass(frozen=True, slots=True)
class Download:
    content: bytes
    content_type: str
    truncated: bool  # the body was larger than the cap; `content` holds the first bytes


async def download(
    client: httpx.AsyncClient,
    url: str,
    policy: RetryPolicy,
    max_bytes: int,
    deadline_seconds: float,
    stop_at: tuple[bytes, ...] = (),
) -> Download:
    """Stream a body without ever holding more than `max_bytes` of it in memory.

    Reading also stops as soon as any `stop_at` marker has been received.

    httpx timeouts apply to each network operation, so a server trickling a byte at
    a time could keep a download alive forever; `deadline_seconds` bounds the whole
    thing, retries included, and raises `TimeoutError` when exceeded.
    """
    overlap = max((len(marker) for marker in stop_at), default=1) - 1
    async with asyncio.timeout(deadline_seconds):
        async for attempt in policy.retrying():
            with attempt:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        # A marker may straddle two chunks.
                        search_from = max(len(body) - overlap, 0)
                        body += chunk
                        if len(body) > max_bytes or any(
                            body.find(marker, search_from) != -1 for marker in stop_at
                        ):
                            break
                    return Download(
                        content=bytes(body[:max_bytes]),
                        content_type=response.headers.get("content-type", ""),
                        truncated=len(body) > max_bytes,
                    )
    raise AssertionError("unreachable: tenacity re-raises the last error")
