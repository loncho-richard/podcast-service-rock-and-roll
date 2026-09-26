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
) -> Download:
    """Stream a body without ever holding more than `max_bytes` of it in memory.

    httpx timeouts apply to each network operation, so a server trickling a byte at
    a time could keep a download alive forever; `deadline_seconds` bounds the whole
    thing, retries included, and raises `TimeoutError` when exceeded.
    """
    async with asyncio.timeout(deadline_seconds):
        async for attempt in policy.retrying():
            with attempt:
                async with client.stream("GET", url) as response:
                    response.raise_for_status()
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in response.aiter_bytes():
                        chunks.append(chunk)
                        size += len(chunk)
                        if size > max_bytes:
                            break
                    return Download(
                        content=b"".join(chunks)[:max_bytes],
                        content_type=response.headers.get("content-type", ""),
                        truncated=size > max_bytes,
                    )
    raise AssertionError("unreachable: tenacity re-raises the last error")
