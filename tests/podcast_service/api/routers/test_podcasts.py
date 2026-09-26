import csv
import io
import json
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from podcast_service.domain.podcast.entities import Podcast

pytestmark = pytest.mark.usefixtures("live_database")

VOLATILE = props("id", "external_id", "created_at", "updated_at")
ALL_TITLES = ["Classic Rock Hour", "Metal 100%_Loud", "Punk Tapes", "Rock Nacional"]


def _titles(body: dict[str, Any]) -> list[str]:
    return [item["title"] for item in body["items"]]


@pytest.mark.parametrize("path", ["/podcasts", f"/podcasts/{uuid4()}", "/podcasts/export"])
async def test_podcast_endpoints_require_authentication(client: AsyncClient, path: str) -> None:
    response = await client.get(path)

    assert response.status_code == 401


# --- list ---------------------------------------------------------------------


@pytest.mark.usefixtures("stored_catalog")
async def test_list_returns_a_page_of_podcasts(
    client: AsyncClient, auth_headers: dict[str, str], snapshot: SnapshotAssertion
) -> None:
    response = await client.get("/podcasts", params={"page_size": 2}, headers=auth_headers)

    assert {"status_code": response.status_code, "body": response.json()} == snapshot(
        exclude=VOLATILE
    )


@pytest.mark.usefixtures("stored_catalog")
@pytest.mark.parametrize(
    ("params", "expected_titles"),
    [
        ({}, ALL_TITLES),
        ({"q": "   "}, ALL_TITLES),
        ({"q": "rock"}, ["Classic Rock Hour", "Rock Nacional"]),
        ({"q": "RADIO"}, ["Classic Rock Hour", "Rock Nacional"]),
        ({"genre": "Music History"}, ["Classic Rock Hour"]),
        ({"language": "en"}, ["Classic Rock Hour", "Punk Tapes"]),
        ({"q": "rock", "language": "es-AR"}, ["Rock Nacional"]),
        ({"q": "jazz"}, []),
    ],
    ids=[
        "all",
        "blank-search-ignored",
        "search-title",
        "search-author",
        "genre",
        "language",
        "combined",
        "none",
    ],
)
async def test_list_filters(
    client: AsyncClient,
    auth_headers: dict[str, str],
    params: dict[str, str],
    expected_titles: list[str],
) -> None:
    response = await client.get("/podcasts", params=params, headers=auth_headers)

    assert _titles(response.json()) == expected_titles


@pytest.mark.usefixtures("stored_catalog")
async def test_list_pagination_metadata(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.get(
        "/podcasts", params={"page": 2, "page_size": 3}, headers=auth_headers
    )

    body = response.json()
    assert {key: body[key] for key in ("page", "page_size", "total", "total_pages")} | {
        "titles": _titles(body)
    } == {"page": 2, "page_size": 3, "total": 4, "total_pages": 2, "titles": ["Rock Nacional"]}


@pytest.mark.parametrize(
    "params",
    [{"page": 0}, {"page_size": 101}, {"q": "x" * 101}, {"language": "english!"}],
    ids=["page-zero", "page-size-too-big", "query-too-long", "bad-language"],
)
async def test_list_rejects_invalid_parameters(
    client: AsyncClient,
    auth_headers: dict[str, str],
    snapshot: SnapshotAssertion,
    params: dict[str, Any],
) -> None:
    response = await client.get("/podcasts", params=params, headers=auth_headers)

    assert {"status_code": response.status_code, "body": response.json()} == snapshot


# --- get ----------------------------------------------------------------------


async def test_get_returns_the_podcast(
    client: AsyncClient, auth_headers: dict[str, str], stored_catalog: list[Podcast]
) -> None:
    podcast = stored_catalog[0]

    response = await client.get(f"/podcasts/{podcast.id}", headers=auth_headers)

    assert (response.status_code, response.json()["id"], response.json()["title"]) == (
        200,
        str(podcast.id),
        podcast.title,
    )


@pytest.mark.parametrize(
    "podcast_id",
    ["00000000-0000-0000-0000-000000000000", "not-a-uuid"],
    ids=["unknown", "malformed"],
)
async def test_get_errors(
    client: AsyncClient,
    auth_headers: dict[str, str],
    snapshot: SnapshotAssertion,
    podcast_id: str,
) -> None:
    response = await client.get(f"/podcasts/{podcast_id}", headers=auth_headers)

    assert {"status_code": response.status_code, "body": response.json()} == snapshot


# --- export -------------------------------------------------------------------


@pytest.mark.usefixtures("stored_catalog")
async def test_export_streams_ndjson_by_default(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get("/podcasts/export", headers=auth_headers)

    assert (
        response.headers["content-type"],
        response.headers["content-disposition"],
        [json.loads(line)["title"] for line in response.text.splitlines()],
    ) == ("application/x-ndjson", 'attachment; filename="podcasts.ndjson"', ALL_TITLES)


@pytest.mark.usefixtures("stored_catalog")
async def test_export_as_csv(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    response = await client.get("/podcasts/export", params={"format": "csv"}, headers=auth_headers)

    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert (
        response.headers["content-type"],
        response.headers["content-disposition"],
        [row["title"] for row in rows],
        rows[0]["genres"],
    ) == (
        "text/csv; charset=utf-8",
        'attachment; filename="podcasts.csv"',
        ALL_TITLES,
        "Music|Music History",
    )


async def test_export_of_an_empty_catalog_is_empty(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get("/podcasts/export", headers=auth_headers)

    assert (response.status_code, response.text) == (200, "")


async def test_export_rejects_unknown_formats(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    response = await client.get("/podcasts/export", params={"format": "xml"}, headers=auth_headers)

    assert (response.status_code, response.json()["error"]["code"]) == (422, "validation_error")
