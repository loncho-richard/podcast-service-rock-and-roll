from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class RawPodcastRecord:
    """A podcast as received from a source, before any cleaning.

    Source adapters only coerce types (anything unusable becomes None); all
    semantic cleaning and validation happens in `PodcastNormalizer`.
    """

    source: str
    external_id: str | None = None
    title: str | None = None
    author: str | None = None
    description: str | None = None
    language: str | None = None
    country: str | None = None
    genres: tuple[str, ...] = ()
    primary_genre: str | None = None
    feed_url: str | None = None
    store_url: str | None = None
    artwork_url: str | None = None
    explicit: bool | None = None
    episode_count: int | None = None
    released_at: str | None = None
