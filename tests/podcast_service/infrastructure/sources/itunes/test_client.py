from collections.abc import Callable

import httpx
import pytest
import respx

from factories import build_itunes_response, build_itunes_result
from podcast_service.domain.ingestion.errors import SourceUnavailableError
from podcast_service.domain.ingestion.ports import SourceBatch
from podcast_service.domain.ingestion.summary import SourceMode
from podcast_service.infrastructure.sources.itunes.client import ITunesPodcastSource

SEARCH_URL = "https://itunes.test/search"
LOOKUP_URL = "https://itunes.test/lookup"


def _ok(*collection_ids: int) -> httpx.Response:
    return httpx.Response(
        200, json=build_itunes_response(*(build_itunes_result(i) for i in collection_ids))
    )


def _unreachable(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("unreachable", request=request)


def _ids(batch: SourceBatch) -> list[str | None]:
    return [record.external_id for record in batch.records]


# --- search -------------------------------------------------------------------


async def test_search_queries_podcasts_for_each_term(
    respx_mock: respx.MockRouter, source: ITunesPodcastSource
) -> None:
    route = respx_mock.get(SEARCH_URL).mock(return_value=_ok(1))

    await source.search(["classic rock"], limit=25)

    assert dict(route.calls.last.request.url.params) == {
        "term": "classic rock",
        "media": "podcast",
        "entity": "podcast",
        "limit": "25",
        "country": "US",
    }


async def test_search_merges_terms_and_keeps_one_copy_per_show(
    respx_mock: respx.MockRouter, source: ITunesPodcastSource
) -> None:
    respx_mock.get(SEARCH_URL).mock(side_effect=[_ok(1, 2), _ok(2, 3)])

    batch = await source.search(["classic rock", "hard rock"], limit=25)

    assert (_ids(batch), batch.mode) == (["1", "2", "3"], SourceMode.LIVE)


async def test_search_retries_transient_failures(
    respx_mock: respx.MockRouter, source: ITunesPodcastSource
) -> None:
    route = respx_mock.get(SEARCH_URL).mock(
        side_effect=[httpx.Response(503), httpx.ConnectTimeout("slow"), _ok(1)]
    )

    batch = await source.search(["classic rock"], limit=25)

    assert (route.call_count, _ids(batch), batch.mode) == (3, ["1"], SourceMode.LIVE)


async def test_search_keeps_live_results_when_only_some_terms_fail(
    respx_mock: respx.MockRouter, source: ITunesPodcastSource
) -> None:
    respx_mock.get(SEARCH_URL).mock(side_effect=[_ok(1), httpx.Response(403)])

    batch = await source.search(["classic rock", "hard rock"], limit=25)

    assert (_ids(batch), batch.mode) == (["1"], SourceMode.LIVE)


@pytest.mark.parametrize(
    "respond",
    [
        lambda _: httpx.Response(503),
        lambda _: httpx.Response(429, headers={"Retry-After": "0"}),
        _unreachable,
        lambda _: httpx.Response(200, text="<html>maintenance</html>"),
        lambda _: httpx.Response(200, json={"unexpected": True}),
    ],
    ids=["server-error", "rate-limited", "unreachable", "not-json", "unexpected-json"],
)
async def test_search_serves_the_stored_sample_when_the_source_is_unavailable(
    respx_mock: respx.MockRouter,
    source: ITunesPodcastSource,
    respond: Callable[[httpx.Request], httpx.Response],
) -> None:
    respx_mock.get(SEARCH_URL).mock(side_effect=respond)

    batch = await source.search(["classic rock", "hard rock"], limit=25)

    assert (_ids(batch), batch.mode) == (["9001", "9002"], SourceMode.FALLBACK)


# --- lookup -------------------------------------------------------------------


async def test_lookup_returns_the_podcast(
    respx_mock: respx.MockRouter, source: ITunesPodcastSource
) -> None:
    respx_mock.get(LOOKUP_URL).mock(return_value=_ok(1001))

    record = await source.lookup("1001")

    assert record is not None
    assert (record.external_id, record.title) == ("1001", "Classic Rock Hour")


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, json=build_itunes_response()),
        httpx.Response(200, json=build_itunes_response(build_itunes_result(1, kind="song"))),
        httpx.Response(400, json={"errorMessage": "Invalid value(s) for key(s): [id]"}),
    ],
    ids=["no-results", "not-a-podcast", "invalid-id"],
)
async def test_lookup_returns_none_when_there_is_no_such_podcast(
    respx_mock: respx.MockRouter, source: ITunesPodcastSource, response: httpx.Response
) -> None:
    respx_mock.get(LOOKUP_URL).mock(return_value=response)

    assert await source.lookup("1001") is None


async def test_lookup_falls_back_to_the_sample_when_the_source_is_down(
    respx_mock: respx.MockRouter, source: ITunesPodcastSource
) -> None:
    respx_mock.get(LOOKUP_URL).mock(return_value=httpx.Response(503))

    record = await source.lookup("9002")

    assert record is not None
    assert record.external_id == "9002"


async def test_lookup_raises_when_the_source_is_down_and_the_sample_lacks_it(
    respx_mock: respx.MockRouter, source: ITunesPodcastSource
) -> None:
    respx_mock.get(LOOKUP_URL).mock(side_effect=httpx.ConnectError("unreachable"))

    with pytest.raises(SourceUnavailableError):
        await source.lookup("1001")
