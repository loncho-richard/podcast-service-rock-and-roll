from factories import build_itunes_result
from podcast_service.domain.ingestion.raw import RawPodcastRecord
from podcast_service.infrastructure.sources.itunes.mapper import map_result


def test_itunes_result_is_mapped_field_by_field() -> None:
    assert map_result(build_itunes_result(1001)) == RawPodcastRecord(
        source="itunes",
        external_id="1001",
        title="Classic Rock Hour",
        author="Rock Radio Network",
        country="USA",
        genres=("Music History", "Podcasts", "Music"),
        primary_genre="Music History",
        feed_url="https://feeds.example.com/classic-rock.xml",
        store_url="https://podcasts.apple.com/us/podcast/id1001",
        artwork_url="https://images.example.com/600x600bb.jpg",
        explicit=False,
        episode_count=120,
        released_at="2026-09-01T10:00:00Z",
    )


def test_values_of_unexpected_type_become_none_or_fall_back() -> None:
    messy = build_itunes_result(
        collectionId="not-a-number",
        trackId=77,
        collectionName="   ",
        trackName="Track Name Instead",
        artistName=123,
        genres="Music",
        trackCount=True,
        artworkUrl600=None,
        collectionExplicitness="explicit",
        releaseDate=20260901,
        feedUrl=["https://feeds.example.com"],
    )

    assert map_result(messy) == RawPodcastRecord(
        source="itunes",
        external_id="77",
        title="Track Name Instead",
        author=None,
        country="USA",
        genres=(),
        primary_genre="Music History",
        feed_url=None,
        store_url="https://podcasts.apple.com/us/podcast/id1001",
        artwork_url="https://images.example.com/100x100bb.jpg",
        explicit=True,
        episode_count=None,
        released_at=None,
    )


def test_non_object_results_become_empty_records() -> None:
    assert map_result(["not", "an", "object"]) == RawPodcastRecord(source="itunes")
