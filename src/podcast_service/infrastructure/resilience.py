"""Retry policy for calls to third-party HTTP services.

Only transient failures are retried (network errors, timeouts, 408/425/429/5xx),
with exponential backoff + jitter, honouring `Retry-After` when the server sends it.
Anything else (4xx, bad payloads) fails fast so callers can degrade gracefully.
"""

from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    RetryCallState,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from podcast_service.infrastructure.rate_limit import RateLimiter

RETRYABLE_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})


def is_transient(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS_CODES
    return isinstance(exc, httpx.TransportError)  # timeouts, connection and protocol errors


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 8.0

    def retrying(self) -> AsyncRetrying:
        return AsyncRetrying(
            stop=stop_after_attempt(self.attempts),
            wait=self.wait,
            retry=retry_if_exception(is_transient),
            reraise=True,
        )

    def wait(self, state: RetryCallState) -> float:
        exc = state.outcome.exception() if state.outcome else None
        retry_after = _retry_after_seconds(exc)
        if retry_after is not None:
            return min(retry_after, self.max_delay)
        backoff = wait_exponential_jitter(initial=self.base_delay, max=self.max_delay)
        return float(backoff(state))


async def get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    policy: RetryPolicy,
    params: dict[str, Any] | None = None,
    rate_limiter: RateLimiter | None = None,
) -> httpx.Response:
    """GET that raises `httpx.HTTPStatusError` for non-2xx once retries are exhausted."""
    async for attempt in policy.retrying():
        with attempt:
            if rate_limiter is not None:
                await rate_limiter.acquire()
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response
    raise AssertionError("unreachable: tenacity re-raises the last error")


def _retry_after_seconds(exc: BaseException | None) -> float | None:
    if not isinstance(exc, httpx.HTTPStatusError):
        return None
    value = exc.response.headers.get("Retry-After", "")
    try:
        return max(float(value), 0.0)
    except ValueError:
        return None  # absent, or an HTTP-date we don't bother parsing
