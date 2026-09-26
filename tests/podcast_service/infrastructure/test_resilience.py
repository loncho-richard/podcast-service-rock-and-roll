from collections.abc import Callable

import httpx
import pytest
import respx
from tenacity import AsyncRetrying, RetryCallState

from podcast_service.infrastructure import RetryPolicy, get_with_retry, is_transient

URL = "https://service.test/resource"


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [(408, True), (429, True), (500, True), (503, True), (400, False), (404, False)],
)
def test_only_transient_status_codes_are_retryable(
    status_error: Callable[..., httpx.HTTPStatusError], status_code: int, expected: bool
) -> None:
    assert is_transient(status_error(status_code)) is expected


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (httpx.ConnectTimeout("timed out"), True),
        (httpx.ConnectError("refused"), True),
        (httpx.RemoteProtocolError("broken"), True),
        (ValueError("bad json"), False),
    ],
)
def test_network_failures_are_retryable(exc: Exception, expected: bool) -> None:
    assert is_transient(exc) is expected


@pytest.mark.parametrize(
    ("retry_after", "expected_wait"),
    [("3", 3.0), ("120", 8.0), ("0", 0.0)],
    ids=["honoured", "capped-at-max-delay", "immediate"],
)
def test_wait_honours_retry_after(
    status_error: Callable[..., httpx.HTTPStatusError], retry_after: str, expected_wait: float
) -> None:
    state = RetryCallState(retry_object=AsyncRetrying(), fn=None, args=(), kwargs={})
    error = status_error(429, headers={"Retry-After": retry_after})
    state.set_exception((type(error), error, None))

    assert RetryPolicy(max_delay=8.0).wait(state) == expected_wait


async def test_transient_failures_are_retried_until_success(
    respx_mock: respx.MockRouter, http_client: httpx.AsyncClient, retry_policy: RetryPolicy
) -> None:
    route = respx_mock.get(URL).mock(
        side_effect=[httpx.Response(503), httpx.ConnectTimeout("slow"), httpx.Response(200)]
    )

    response = await get_with_retry(http_client, URL, retry_policy)

    assert (response.status_code, route.call_count) == (200, 3)


async def test_gives_up_after_the_last_attempt(
    respx_mock: respx.MockRouter, http_client: httpx.AsyncClient, retry_policy: RetryPolicy
) -> None:
    route = respx_mock.get(URL).mock(return_value=httpx.Response(503))

    with pytest.raises(httpx.HTTPStatusError):
        await get_with_retry(http_client, URL, retry_policy)
    assert route.call_count == 3


async def test_client_errors_fail_fast(
    respx_mock: respx.MockRouter, http_client: httpx.AsyncClient, retry_policy: RetryPolicy
) -> None:
    route = respx_mock.get(URL).mock(return_value=httpx.Response(404))

    with pytest.raises(httpx.HTTPStatusError):
        await get_with_retry(http_client, URL, retry_policy)
    assert route.call_count == 1
