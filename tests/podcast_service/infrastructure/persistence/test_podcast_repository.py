from dataclasses import replace
from uuid import uuid4

import pytest

from podcast_service.domain.podcast.entities import Podcast
from podcast_service.domain.podcast.filters import PageRequest, PodcastFilters
from podcast_service.domain.podcast.repository import UpsertOutcome
from podcast_service.infrastructure.persistence.podcast_repository import (
    SqlAlchemyPodcastRepository,
)


async def test_upsert_creates_and_round_trips_every_field(
    repository: SqlAlchemyPodcastRepository, podcast: Podcast
) -> None:
    stored, outcome = await repository.upsert(podcast)

    assert (outcome, replace(stored, id=None, created_at=None, updated_at=None)) == (
        UpsertOutcome.CREATED,
        podcast,
    )


async def test_upserting_identical_data_is_idempotent(
    repository: SqlAlchemyPodcastRepository, podcast: Podcast
) -> None:
    first, _ = await repository.upsert(podcast)

    second, outcome = await repository.upsert(podcast)

    assert (outcome, second) == (UpsertOutcome.UNCHANGED, first)


async def test_upserting_changed_data_updates_in_place(
    repository: SqlAlchemyPodcastRepository, podcast: Podcast
) -> None:
    first, _ = await repository.upsert(podcast)

    updated, outcome = await repository.upsert(replace(podcast, title="Classic Rock Hour II"))

    assert (outcome, updated.id, updated.title) == (
        UpsertOutcome.UPDATED,
        first.id,
        "Classic Rock Hour II",
    )


async def test_reingesting_without_enrichment_keeps_the_enriched_fields(
    repository: SqlAlchemyPodcastRepository, podcast: Podcast
) -> None:
    first, _ = await repository.upsert(podcast)

    again, outcome = await repository.upsert(
        replace(podcast, description=None, language=None, palette=None)
    )

    assert (outcome, again) == (UpsertOutcome.UNCHANGED, first)


async def test_get_returns_the_stored_podcast(
    repository: SqlAlchemyPodcastRepository, catalog: list[Podcast]
) -> None:
    assert catalog[0].id is not None
    assert await repository.get(catalog[0].id) == catalog[0]


async def test_get_unknown_id_returns_none(repository: SqlAlchemyPodcastRepository) -> None:
    assert await repository.get(uuid4()) is None


@pytest.mark.usefixtures("catalog")
@pytest.mark.parametrize(
    ("filters", "expected_titles"),
    [
        (
            PodcastFilters(),
            ["Classic Rock Hour", "Metal 100%_Loud", "Punk Tapes", "Rock Nacional"],
        ),
        (PodcastFilters(query="ROCK"), ["Classic Rock Hour", "Rock Nacional"]),
        (PodcastFilters(query="radio"), ["Classic Rock Hour", "Rock Nacional"]),
        (PodcastFilters(query="100%"), ["Metal 100%_Loud"]),
        (PodcastFilters(query="_"), ["Metal 100%_Loud"]),
        (PodcastFilters(genre="Music History"), ["Classic Rock Hour"]),
        (PodcastFilters(language="en"), ["Classic Rock Hour", "Punk Tapes"]),
        (PodcastFilters(language="es-ar"), ["Rock Nacional"]),
        (PodcastFilters(query="rock", language="es"), ["Rock Nacional"]),
        (PodcastFilters(query="jazz"), []),
    ],
    ids=[
        "no-filters",
        "query-title-case-insensitive",
        "query-author",
        "query-escapes-percent",
        "query-escapes-underscore",
        "genre",
        "language-prefix",
        "language-exact",
        "combined",
        "no-match",
    ],
)
async def test_list_filters(
    repository: SqlAlchemyPodcastRepository,
    filters: PodcastFilters,
    expected_titles: list[str],
) -> None:
    page = await repository.list(filters, PageRequest(page=1, page_size=10))

    assert [podcast.title for podcast in page.items] == expected_titles


@pytest.mark.usefixtures("catalog")
async def test_list_paginates_and_reports_the_total(
    repository: SqlAlchemyPodcastRepository,
) -> None:
    page = await repository.list(PodcastFilters(), PageRequest(page=2, page_size=3))

    assert (page.total, [podcast.title for podcast in page.items]) == (4, ["Rock Nacional"])


async def test_stream_all_yields_the_whole_catalog(
    repository: SqlAlchemyPodcastRepository, catalog: list[Podcast]
) -> None:
    streamed = [podcast async for podcast in repository.stream_all()]

    assert streamed == sorted(catalog, key=lambda podcast: podcast.title)
