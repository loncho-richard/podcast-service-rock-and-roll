from collections.abc import Iterable
from dataclasses import replace

from podcast_service.domain.ingestion.ports import FeedDetails
from podcast_service.domain.ingestion.raw import RawPodcastRecord
from podcast_service.domain.ingestion.relevance import RockRelevancePolicy
from podcast_service.domain.ingestion.summary import SkippedRecord, SkipReason
from podcast_service.domain.ingestion.text import (
    clean_text,
    clean_url,
    normalize_language,
    parse_datetime,
)
from podcast_service.domain.podcast import ExternalRef, Podcast

# iTunes tags every show with this catch-all genre; it carries no information.
_GENERIC_GENRES = frozenset({"podcasts"})


class PodcastNormalizer:
    """Turns raw source records into clean `Podcast` aggregates, or explains why not."""

    def __init__(self, relevance: RockRelevancePolicy) -> None:
        self._relevance = relevance

    def normalize(self, raw: RawPodcastRecord) -> Podcast | SkippedRecord:
        external_id = clean_text(raw.external_id)
        title = clean_text(raw.title)
        author = clean_text(raw.author)
        if external_id is None:
            return SkippedRecord(SkipReason.MISSING_EXTERNAL_ID, None, title)
        if title is None:
            return SkippedRecord(SkipReason.MISSING_TITLE, external_id, None)
        if author is None:
            return SkippedRecord(SkipReason.MISSING_AUTHOR, external_id, title)

        genres = _clean_genres(raw.genres)
        if not self._relevance.is_rock_related(title=title, author=author, genres=genres):
            return SkippedRecord(SkipReason.NOT_ROCK_RELATED, external_id, title)

        return Podcast(
            ref=ExternalRef(source=raw.source, external_id=external_id),
            title=title,
            author=author,
            description=clean_text(raw.description),
            language=normalize_language(raw.language),
            country=clean_text(raw.country),
            genres=genres,
            primary_genre=clean_text(raw.primary_genre),
            feed_url=clean_url(raw.feed_url),
            store_url=clean_url(raw.store_url),
            cover_image_url=clean_url(raw.artwork_url),
            explicit=bool(raw.explicit),
            episode_count=_non_negative(raw.episode_count),
            released_at=parse_datetime(raw.released_at),
        )

    def normalize_batch(
        self, records: Iterable[RawPodcastRecord]
    ) -> tuple[list[Podcast], list[SkippedRecord]]:
        """Normalize a batch; later records with an already-seen reference are skipped."""
        podcasts: list[Podcast] = []
        skipped: list[SkippedRecord] = []
        seen: set[ExternalRef] = set()
        for raw in records:
            result = self.normalize(raw)
            if isinstance(result, SkippedRecord):
                skipped.append(result)
            elif result.ref in seen:
                skipped.append(
                    SkippedRecord(
                        SkipReason.DUPLICATE_IN_BATCH, result.ref.external_id, result.title
                    )
                )
            else:
                seen.add(result.ref)
                podcasts.append(result)
        return podcasts, skipped

    def apply_feed_details(self, podcast: Podcast, details: FeedDetails) -> Podcast:
        """Merge cleaned RSS data; feed values only fill in or refine, never erase."""
        return replace(
            podcast,
            description=clean_text(details.description) or podcast.description,
            language=normalize_language(details.language) or podcast.language,
        )


def _clean_genres(genres: Iterable[str]) -> tuple[str, ...]:
    cleaned: dict[str, str] = {}
    for genre in genres:
        text = clean_text(genre)
        if text and text.lower() not in _GENERIC_GENRES:
            cleaned.setdefault(text.lower(), text)
    return tuple(cleaned.values())


def _non_negative(value: int | None) -> int | None:
    return value if value is not None and value >= 0 else None
