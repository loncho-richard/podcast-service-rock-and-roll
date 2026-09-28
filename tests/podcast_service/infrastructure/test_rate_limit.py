from collections.abc import Callable

import pytest

from fakes import FakeClock
from podcast_service.infrastructure import RateLimiter, RateLimitExceededError


async def test_calls_within_the_budget_do_not_wait(
    rate_limiter: RateLimiter, fake_clock: FakeClock
) -> None:
    await rate_limiter.acquire()
    await rate_limiter.acquire()

    assert fake_clock.sleeps == []


async def test_a_call_over_budget_waits_until_the_oldest_slot_frees(
    rate_limiter: RateLimiter, fake_clock: FakeClock
) -> None:
    await rate_limiter.acquire()
    fake_clock.now = 10
    await rate_limiter.acquire()
    fake_clock.now = 45

    await rate_limiter.acquire()

    assert fake_clock.sleeps == [15]  # the first call, at t=0, expires at t=60


async def test_slots_free_up_as_the_window_slides(
    rate_limiter: RateLimiter, fake_clock: FakeClock
) -> None:
    await rate_limiter.acquire()
    await rate_limiter.acquire()
    fake_clock.now = 60

    await rate_limiter.acquire()

    assert fake_clock.sleeps == []


async def test_a_call_that_would_wait_too_long_is_rejected(
    rate_limiter: RateLimiter, fake_clock: FakeClock
) -> None:
    await rate_limiter.acquire()
    await rate_limiter.acquire()
    fake_clock.now = 5

    with pytest.raises(RateLimitExceededError):
        await rate_limiter.acquire()  # would need 55 s, more than the 30 s allowed


async def test_waits_and_rejections_are_counted(
    rate_limiter: RateLimiter,
    fake_clock: FakeClock,
    metric_delta: Callable[..., Callable[[], float]],
) -> None:
    waited = metric_delta("rate_limited_calls_total", upstream="test", outcome="waited")
    rejected = metric_delta("rate_limited_calls_total", upstream="test", outcome="rejected")
    await rate_limiter.acquire()
    await rate_limiter.acquire()
    fake_clock.now = 5
    with pytest.raises(RateLimitExceededError):
        await rate_limiter.acquire()
    fake_clock.now = 45

    await rate_limiter.acquire()

    assert (waited(), rejected()) == (1, 1)
