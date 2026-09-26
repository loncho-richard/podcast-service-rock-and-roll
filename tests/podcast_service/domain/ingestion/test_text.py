from datetime import UTC, datetime

import pytest

from podcast_service.domain.ingestion.text import (
    clean_text,
    clean_url,
    normalize_language,
    parse_datetime,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("   ", None),
        ("  Rock \n\t Hour ", "Rock Hour"),
        ("<p>Line one<br/>line two</p>", "Line one line two"),
        ("AC&#47;DC &amp; friends", "AC/DC & friends"),
        ("Guns &amp;amp; Roses", "Guns & Roses"),
        ("<style>p{}</style>Visible<script>alert(1)</script>", "Visible"),
        ("Rock < Pop", "Rock < Pop"),
    ],
)
def test_clean_text(value: str | None, expected: str | None) -> None:
    assert clean_text(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("en", "en"),
        ("EN", "en"),
        ("en-us", "en-US"),
        (" es_AR ", "es-AR"),
        ("zh-Hant", "zh-hant"),
        ("English", None),
        ("", None),
    ],
)
def test_normalize_language(value: str | None, expected: str | None) -> None:
    assert normalize_language(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (" https://example.com/feed.xml ", "https://example.com/feed.xml"),
        ("http://example.com", "http://example.com"),
        ("ftp://example.com/feed.xml", None),
        ("javascript:alert(1)", None),
        ("/relative/path", None),
    ],
)
def test_clean_url(value: str | None, expected: str | None) -> None:
    assert clean_url(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("2026-09-01T10:00:00Z", datetime(2026, 9, 1, 10, 0, tzinfo=UTC)),
        ("2026-09-01T07:00:00-03:00", datetime(2026, 9, 1, 10, 0, tzinfo=UTC)),
        ("2026-09-01", datetime(2026, 9, 1, tzinfo=UTC)),
        ("Tue, 01 Sep 2026 10:00:00 GMT", datetime(2026, 9, 1, 10, 0, tzinfo=UTC)),
        ("not a date", None),
    ],
)
def test_parse_datetime(value: str | None, expected: datetime | None) -> None:
    assert parse_datetime(value) == expected
