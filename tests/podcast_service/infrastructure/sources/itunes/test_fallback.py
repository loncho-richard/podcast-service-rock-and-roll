from podcast_service.infrastructure.sources.itunes.fallback import ITunesSampleFallback
from podcast_service.infrastructure.sources.itunes.mapper import result_id


def test_the_packaged_sample_ships_with_podcasts() -> None:
    results = ITunesSampleFallback().search_results(limit=25)

    assert results
    assert all(result_id(item) for item in results)


def test_limit_applies_per_stored_response(fallback: ITunesSampleFallback) -> None:
    assert [result_id(item) for item in fallback.search_results(limit=1)] == ["9001"]


def test_lookup_finds_a_stored_podcast(fallback: ITunesSampleFallback) -> None:
    assert result_id(fallback.lookup_result("9002")) == "9002"


def test_lookup_of_an_unknown_podcast_returns_none(fallback: ITunesSampleFallback) -> None:
    assert fallback.lookup_result("1") is None
