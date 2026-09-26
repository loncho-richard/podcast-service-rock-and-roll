"""Pure cleaning helpers for messy upstream data. Every helper returns None for unusable input."""

import html
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit

_WHITESPACE = re.compile(r"\s+")
_LANGUAGE = re.compile(r"^([a-z]{2,3})(?:[-_]([a-z0-9]{2,8}))?$", re.IGNORECASE)
_NON_TEXT_TAGS = frozenset({"script", "style"})


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skipping = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _NON_TEXT_TAGS:
            self._skipping += 1
        self.parts.append(" ")  # "a<br>b" must not become "ab"

    def handle_endtag(self, tag: str) -> None:
        if tag in _NON_TEXT_TAGS and self._skipping:
            self._skipping -= 1
        self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if not self._skipping:
            self.parts.append(data)


def clean_text(value: str | None) -> str | None:
    """Strip HTML tags, decode entities (feeds are often double-escaped), collapse whitespace."""
    if value is None:
        return None
    parser = _TextExtractor()
    parser.feed(value)
    parser.close()
    text = html.unescape("".join(parser.parts))
    text = _WHITESPACE.sub(" ", text).strip()
    return text or None


def normalize_language(value: str | None) -> str | None:
    """`en-us` / `EN_us` -> `en-US`, `EN` -> `en`. Anything that is not a language tag -> None."""
    if value is None:
        return None
    match = _LANGUAGE.match(value.strip())
    if not match:
        return None
    language, region = match.group(1).lower(), match.group(2)
    if region is None:
        return language
    return f"{language}-{region.upper() if len(region) == 2 else region.lower()}"


def clean_url(value: str | None) -> str | None:
    """Only absolute http(s) URLs are kept."""
    if value is None:
        return None
    url = value.strip()
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return None
    return url


def parse_datetime(value: str | None) -> datetime | None:
    """Accept ISO-8601 (iTunes) and RFC 2822 (RSS). Naive values are assumed to be UTC."""
    if value is None or not value.strip():
        return None
    raw = value.strip()
    parsed: datetime | None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            parsed = None
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
