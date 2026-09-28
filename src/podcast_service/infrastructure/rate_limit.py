import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable

from podcast_service.infrastructure.observability import record_rate_limit


class RateLimitExceededError(Exception):
    pass


class RateLimiter:
    """Sliding window: at most `max_calls` per `period` seconds across the process.

    A caller over budget waits for a free slot, unless that would take longer than
    `max_wait`, in which case `RateLimitExceededError` is raised instead.
    """

    def __init__(
        self,
        name: str,
        max_calls: int,
        period: float,
        max_wait: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._name = name
        self._max_calls = max_calls
        self._period = period
        self._max_wait = max_wait
        self._clock = clock
        self._sleep = sleep
        self._calls: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            self._forget_expired()
            if len(self._calls) >= self._max_calls:
                wait = self._calls[0] + self._period - self._clock()
                if wait > self._max_wait:
                    record_rate_limit(self._name, waited=False)
                    raise RateLimitExceededError(
                        f"{self._name}: {self._max_calls} calls per {self._period:g}s exhausted"
                    )
                record_rate_limit(self._name, waited=True)
                await self._sleep(wait)
                self._forget_expired()
            self._calls.append(self._clock())

    def _forget_expired(self) -> None:
        now = self._clock()
        while self._calls and now - self._calls[0] >= self._period:
            self._calls.popleft()
