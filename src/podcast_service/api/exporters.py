"""Serializers for the catalog export. Both write rows as they arrive from the DB cursor."""

import csv
import io
from collections.abc import AsyncIterable, AsyncIterator, Callable
from enum import StrEnum

from podcast_service.api.schemas.podcasts import PodcastResponse
from podcast_service.domain.podcast.entities import Podcast

_ROWS_PER_CHUNK = 200  # fewer, larger writes than one per row
_LIST_SEPARATOR = "|"
# Cells starting with these are evaluated as formulas by spreadsheet apps.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
CSV_COLUMNS = list(PodcastResponse.model_fields)


class ExportFormat(StrEnum):
    NDJSON = "ndjson"
    CSV = "csv"

    @property
    def media_type(self) -> str:
        return {"ndjson": "application/x-ndjson", "csv": "text/csv; charset=utf-8"}[self.value]


def export_stream(
    podcasts: AsyncIterable[Podcast], export_format: ExportFormat
) -> AsyncIterator[str]:
    if export_format is ExportFormat.CSV:
        return _chunked(podcasts, _csv_row, header=_csv_line(CSV_COLUMNS))
    return _chunked(podcasts, _ndjson_row)


async def _chunked(
    podcasts: AsyncIterable[Podcast], render: Callable[[Podcast], str], header: str = ""
) -> AsyncIterator[str]:
    buffer = [header] if header else []
    async for podcast in podcasts:
        buffer.append(render(podcast))
        if len(buffer) >= _ROWS_PER_CHUNK:
            yield "".join(buffer)
            buffer.clear()
    if buffer:
        yield "".join(buffer)


def _ndjson_row(podcast: Podcast) -> str:
    return PodcastResponse.from_domain(podcast).model_dump_json() + "\n"


def _csv_row(podcast: Podcast) -> str:
    data = PodcastResponse.from_domain(podcast).model_dump(mode="json")
    return _csv_line([_csv_cell(data[column]) for column in CSV_COLUMNS])


def _csv_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return _LIST_SEPARATOR.join(str(item) for item in value)
    text = str(value)
    return f"'{text}" if text.startswith(_FORMULA_PREFIXES) else text


def _csv_line(cells: list[str]) -> str:
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="\n").writerow(cells)
    return buffer.getvalue()
