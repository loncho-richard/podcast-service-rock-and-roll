from dataclasses import replace
from typing import Any

import pytest

from factories import RawPodcastRecordFactory
from podcast_service.domain.ingestion.normalizer import PodcastNormalizer
from podcast_service.domain.ingestion.ports import FeedDetails
from podcast_service.domain.ingestion.raw import RawPodcastRecord
from podcast_service.domain.ingestion.summary import SkippedRecord, SkipReason
from podcast_service.domain.podcast.entities import Podcast


def test_valid_record_becomes_a_clean_podcast(
    normalizer: PodcastNormalizer, raw_record: RawPodcastRecord, expected_podcast: Podcast
) -> None:
    assert normalizer.normalize(raw_record) == expected_podcast


def test_messy_fields_are_cleaned_instead_of_rejected(
    normalizer: PodcastNormalizer, raw_record: RawPodcastRecord, expected_podcast: Podcast
) -> None:
    messy = replace(
        raw_record,
        title="  <b>Classic&nbsp;Rock</b>   Hour ",
        author="Rock Radio &amp;amp; Friends",
        description="<p>Stories behind<br>the <i>greatest</i> records.</p><script>x()</script>",
        language="EN_us",
        genres=("Music", " music ", "Podcasts", "Music History", ""),
        feed_url="ftp://feeds.example.com/rock.xml",
        store_url="not a url",
        episode_count=-3,
        released_at="sometime last year",
        explicit=None,
    )

    expected = replace(
        expected_podcast,
        author="Rock Radio & Friends",
        description="Stories behind the greatest records.",
        feed_url=None,
        store_url=None,
        episode_count=None,
        released_at=None,
    )
    assert normalizer.normalize(messy) == expected


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        (
            {"external_id": "  "},
            SkippedRecord(SkipReason.MISSING_EXTERNAL_ID, None, "Classic Rock Hour"),
        ),
        ({"title": "<p> </p>"}, SkippedRecord(SkipReason.MISSING_TITLE, "1001", None)),
        (
            {"author": None},
            SkippedRecord(SkipReason.MISSING_AUTHOR, "1001", "Classic Rock Hour"),
        ),
        (
            {"title": "Jazz Standards Weekly", "author": "Blue Note Radio"},
            SkippedRecord(SkipReason.NOT_ROCK_RELATED, "1001", "Jazz Standards Weekly"),
        ),
    ],
    ids=["missing-id", "html-only-title", "missing-author", "not-rock"],
)
def test_unusable_records_are_skipped_with_a_reason(
    normalizer: PodcastNormalizer,
    raw_record: RawPodcastRecord,
    overrides: dict[str, Any],
    expected: SkippedRecord,
) -> None:
    assert normalizer.normalize(replace(raw_record, **overrides)) == expected


def test_batch_keeps_first_occurrence_and_skips_duplicates(
    normalizer: PodcastNormalizer,
) -> None:
    records = [
        RawPodcastRecordFactory.build(external_id="1"),
        RawPodcastRecordFactory.build(external_id=" 1 ", title="Classic Rock Hour (mirror)"),
        RawPodcastRecordFactory.build(external_id="2"),
    ]

    podcasts, skipped = normalizer.normalize_batch(records)

    assert ([p.ref.external_id for p in podcasts], skipped) == (
        ["1", "2"],
        [SkippedRecord(SkipReason.DUPLICATE_IN_BATCH, "1", "Classic Rock Hour (mirror)")],
    )


@pytest.mark.parametrize(
    ("details", "expected_description", "expected_language"),
    [
        (
            FeedDetails(description="<p>Deep cuts &amp; B-sides</p>", language="es-ar"),
            "Deep cuts & B-sides",
            "es-AR",
        ),
        (
            FeedDetails(description="  ", language="not a language"),
            "Stories behind the greatest rock records.",
            "en-US",
        ),
    ],
    ids=["feed-refines", "empty-feed-keeps-existing"],
)
def test_feed_details_fill_in_but_never_erase(
    normalizer: PodcastNormalizer,
    expected_podcast: Podcast,
    details: FeedDetails,
    expected_description: str,
    expected_language: str,
) -> None:
    enriched = normalizer.apply_feed_details(expected_podcast, details)

    assert (enriched.description, enriched.language) == (expected_description, expected_language)
