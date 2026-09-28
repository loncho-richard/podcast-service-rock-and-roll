from collections.abc import AsyncIterator, Callable

import httpx
import pytest

from fakes import FakeClock
from podcast_service.infrastructure import RateLimiter, RetryPolicy


@pytest.fixture
def retry_policy() -> RetryPolicy:
    """Three attempts with no waiting, so retry tests run instantly."""
    return RetryPolicy(attempts=3, base_delay=0, max_delay=0)


@pytest.fixture
async def http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
def status_error() -> Callable[..., httpx.HTTPStatusError]:
    def build(status_code: int, headers: dict[str, str] | None = None) -> httpx.HTTPStatusError:
        request = httpx.Request("GET", "https://service.test/")
        response = httpx.Response(status_code, headers=headers, request=request)
        return httpx.HTTPStatusError("failed", request=request, response=response)

    return build


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def rate_limiter(fake_clock: FakeClock) -> RateLimiter:
    """2 calls per minute, willing to wait up to 30 s for a slot."""
    return RateLimiter(
        "test", max_calls=2, period=60, max_wait=30, clock=fake_clock, sleep=fake_clock.sleep
    )


@pytest.fixture
def single_call_limiter(fake_clock: FakeClock) -> RateLimiter:
    """1 call per minute and never waits: every call after the first is rejected."""
    return RateLimiter(
        "test", max_calls=1, period=60, max_wait=0, clock=fake_clock, sleep=fake_clock.sleep
    )


@pytest.fixture
def patient_single_call_limiter(fake_clock: FakeClock) -> RateLimiter:
    return RateLimiter(
        "test", max_calls=1, period=60, max_wait=120, clock=fake_clock, sleep=fake_clock.sleep
    )
