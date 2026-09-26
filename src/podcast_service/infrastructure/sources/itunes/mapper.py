"""Maps iTunes Search/Lookup results to `RawPodcastRecord`.

Only type coercion happens here: values of an unexpected type become None and the
domain normalizer decides what is usable.
"""

from typing import Any

from podcast_service.domain.ingestion import RawPodcastRecord

SOURCE_NAME = "itunes"


def map_result(item: Any) -> RawPodcastRecord:
    if not isinstance(item, dict):
        return RawPodcastRecord(source=SOURCE_NAME)
    return RawPodcastRecord(
        source=SOURCE_NAME,
        external_id=result_id(item),
        title=_first_str(item, "collectionName", "trackName"),
        author=_first_str(item, "artistName"),
        country=_first_str(item, "country"),
        genres=_genres(item.get("genres")),
        primary_genre=_first_str(item, "primaryGenreName"),
        feed_url=_first_str(item, "feedUrl"),
        store_url=_first_str(item, "collectionViewUrl", "trackViewUrl"),
        artwork_url=_first_str(item, "artworkUrl600", "artworkUrl100", "artworkUrl60"),
        explicit=_explicit(item.get("collectionExplicitness")),
        episode_count=_integer(item.get("trackCount")),
        released_at=_first_str(item, "releaseDate"),
    )


def result_id(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    return _identifier(item.get("collectionId")) or _identifier(item.get("trackId"))


def _first_str(item: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _genres(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(genre for genre in value if isinstance(genre, str))


def _identifier(value: Any) -> str | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str) and value.strip().isdigit():
        return value.strip()
    return None


def _integer(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _explicit(value: Any) -> bool | None:
    if value == "explicit":
        return True
    if value in {"notExplicit", "cleaned"}:
        return False
    return None
