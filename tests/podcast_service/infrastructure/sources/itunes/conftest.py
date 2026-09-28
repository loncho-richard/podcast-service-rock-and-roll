import json
from pathlib import Path

import httpx
import pytest

from factories import build_itunes_response, build_itunes_result
from podcast_service.infrastructure import RateLimiter, RetryPolicy
from podcast_service.infrastructure.sources.itunes import ITunesPodcastSource, ITunesSampleFallback

ITUNES_BASE_URL = "https://itunes.test"


@pytest.fixture
def sample_path(tmp_path: Path) -> Path:
    """A tiny fallback sample with podcasts 9001 and 9002."""
    path = tmp_path / "sample.json"
    document = {
        "responses": {
            "rock": build_itunes_response(build_itunes_result(9001), build_itunes_result(9002)),
        }
    }
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


@pytest.fixture
def fallback(sample_path: Path) -> ITunesSampleFallback:
    return ITunesSampleFallback(sample_path)


def _source(
    http_client: httpx.AsyncClient,
    retry_policy: RetryPolicy,
    rate_limiter: RateLimiter,
    fallback: ITunesSampleFallback,
) -> ITunesPodcastSource:
    return ITunesPodcastSource(
        http_client=http_client,
        base_url=ITUNES_BASE_URL,
        country="US",
        retry_policy=retry_policy,
        rate_limiter=rate_limiter,
        fallback=fallback,
    )


@pytest.fixture
def source(
    http_client: httpx.AsyncClient, retry_policy: RetryPolicy, fallback: ITunesSampleFallback
) -> ITunesPodcastSource:
    unlimited = RateLimiter("itunes", max_calls=1_000, period=60, max_wait=0)
    return _source(http_client, retry_policy, unlimited, fallback)


@pytest.fixture
def rate_limited_source(
    http_client: httpx.AsyncClient,
    retry_policy: RetryPolicy,
    single_call_limiter: RateLimiter,
    fallback: ITunesSampleFallback,
) -> ITunesPodcastSource:
    return _source(http_client, retry_policy, single_call_limiter, fallback)
