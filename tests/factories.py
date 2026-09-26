"""Polyfactory factories shared by the whole suite. Defaults describe a valid rock podcast."""

from datetime import UTC, datetime
from itertools import count
from typing import Any

from polyfactory import Use
from polyfactory.factories import DataclassFactory

from podcast_service.domain.ingestion.raw import RawPodcastRecord
from podcast_service.domain.podcast.entities import Podcast
from podcast_service.domain.podcast.value_objects import ColorPalette, ExternalRef

_external_ids = count(1000)


class RawPodcastRecordFactory(DataclassFactory[RawPodcastRecord]):
    source = "itunes"
    external_id = Use(lambda: str(next(_external_ids)))
    title = "Classic Rock Hour"
    author = "Rock Radio Network"
    description = "Stories behind the greatest rock records."
    language = "en-us"
    country = "USA"
    genres = ("Music", "Music History", "Podcasts")
    primary_genre = "Music"
    feed_url = "https://feeds.example.com/classic-rock.xml"
    store_url = "https://podcasts.apple.com/podcast/id1000"
    artwork_url = "https://images.example.com/classic-rock.jpg"
    explicit = False
    episode_count = 120
    released_at = "2026-09-01T10:00:00Z"


class PodcastFactory(DataclassFactory[Podcast]):
    ref = Use(lambda: ExternalRef(source="itunes", external_id=str(next(_external_ids))))
    title = "Classic Rock Hour"
    author = "Rock Radio Network"
    description = "Stories behind the greatest rock records."
    language = "en-US"
    country = "USA"
    genres = ("Music", "Music History")
    primary_genre = "Music"
    feed_url = "https://feeds.example.com/classic-rock.xml"
    store_url = "https://podcasts.apple.com/podcast/id1000"
    cover_image_url = "https://images.example.com/classic-rock.jpg"
    palette = Use(lambda: ColorPalette.from_hex(["#1a1a1a", "#c0392b", "#f5f5f5"]))
    explicit = False
    episode_count = 120
    released_at = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)
    id = None
    created_at = None
    updated_at = None


def build_itunes_result(collection_id: int = 1001, **overrides: Any) -> dict[str, Any]:
    """A podcast item shaped exactly like the iTunes Search/Lookup API returns it."""
    return {
        "wrapperType": "track",
        "kind": "podcast",
        "collectionId": collection_id,
        "trackId": collection_id,
        "artistName": "Rock Radio Network",
        "collectionName": "Classic Rock Hour",
        "trackName": "Classic Rock Hour",
        "collectionViewUrl": f"https://podcasts.apple.com/us/podcast/id{collection_id}",
        "feedUrl": "https://feeds.example.com/classic-rock.xml",
        "artworkUrl100": "https://images.example.com/100x100bb.jpg",
        "artworkUrl600": "https://images.example.com/600x600bb.jpg",
        "releaseDate": "2026-09-01T10:00:00Z",
        "collectionExplicitness": "notExplicit",
        "trackCount": 120,
        "country": "USA",
        "primaryGenreName": "Music History",
        "genres": ["Music History", "Podcasts", "Music"],
        **overrides,
    }


def build_itunes_response(*results: dict[str, Any]) -> dict[str, Any]:
    return {"resultCount": len(results), "results": list(results)}
