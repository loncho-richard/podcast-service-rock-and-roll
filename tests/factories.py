"""Polyfactory factories shared by the whole suite. Defaults describe a valid rock podcast."""

from itertools import count

from polyfactory import Use
from polyfactory.factories import DataclassFactory

from podcast_service.domain.ingestion.raw import RawPodcastRecord

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
