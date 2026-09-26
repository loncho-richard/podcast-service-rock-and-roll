from collections.abc import AsyncIterator, Callable

import httpx
import pytest

from podcast_service.infrastructure import RetryPolicy


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
