import json

import pytest
from syrupy.assertion import SnapshotAssertion

from fakes import as_stream
from podcast_service.api import CSV_COLUMNS, ExportFormat, export_stream
from podcast_service.domain.podcast import Podcast


@pytest.mark.parametrize("export_format", list(ExportFormat))
async def test_export_output(
    stored_podcasts: list[Podcast], snapshot: SnapshotAssertion, export_format: ExportFormat
) -> None:
    chunks = [chunk async for chunk in export_stream(as_stream(stored_podcasts), export_format)]

    assert "".join(chunks) == snapshot


async def test_ndjson_has_one_json_object_per_podcast(stored_podcasts: list[Podcast]) -> None:
    stream = export_stream(as_stream(stored_podcasts), ExportFormat.NDJSON)

    body = "".join([chunk async for chunk in stream])

    assert [json.loads(line)["id"] for line in body.splitlines()] == [
        str(podcast.id) for podcast in stored_podcasts
    ]


@pytest.mark.parametrize("export_format", list(ExportFormat))
async def test_rows_are_written_in_chunks(
    many_stored_podcasts: list[Podcast], export_format: ExportFormat
) -> None:
    stream = export_stream(as_stream(many_stored_podcasts), export_format)

    chunks = [chunk async for chunk in stream]

    assert len(chunks) == 3  # 450 rows, 200 per chunk


@pytest.mark.parametrize(
    ("export_format", "expected_body"),
    [(ExportFormat.NDJSON, ""), (ExportFormat.CSV, ",".join(CSV_COLUMNS) + "\n")],
    ids=["ndjson-is-empty", "csv-has-only-the-header"],
)
async def test_empty_catalog(export_format: ExportFormat, expected_body: str) -> None:
    body = "".join([chunk async for chunk in export_stream(as_stream([]), export_format)])

    assert body == expected_body
