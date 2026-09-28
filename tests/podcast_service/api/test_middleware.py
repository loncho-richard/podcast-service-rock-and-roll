import logging
import re
from collections.abc import Callable

import pytest
from httpx import AsyncClient

GENERATED_ID = re.compile(r"^[0-9a-f]{32}$")


async def test_a_request_id_is_generated_and_returned(observed_client: AsyncClient) -> None:
    response = await observed_client.get("/items/1")

    assert GENERATED_ID.match(response.headers["x-request-id"])


async def test_code_inside_the_request_sees_its_request_id(
    observed_client: AsyncClient,
) -> None:
    response = await observed_client.get("/items/1")

    assert response.json()["request_id"] == response.headers["x-request-id"]


async def test_a_safe_incoming_request_id_is_kept(observed_client: AsyncClient) -> None:
    response = await observed_client.get("/items/1", headers={"X-Request-ID": "gw-7f3a.01_b"})

    assert response.headers["x-request-id"] == "gw-7f3a.01_b"


@pytest.mark.parametrize(
    "incoming",
    ["has spaces", "semi;colon", "x" * 65, ""],
    ids=["spaces", "separator", "too-long", "empty"],
)
async def test_an_unsafe_incoming_request_id_is_replaced(
    observed_client: AsyncClient, incoming: str
) -> None:
    response = await observed_client.get("/items/1", headers={"X-Request-ID": incoming})

    assert GENERATED_ID.match(response.headers["x-request-id"])


async def test_each_request_is_logged_with_its_route_template(
    observed_client: AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="podcast_service.access"):
        await observed_client.get("/items/42")

    [record] = [r for r in caplog.records if r.name == "podcast_service.access"]
    assert {key: getattr(record, key) for key in ("method", "path", "route", "status")} == {
        "method": "GET",
        "path": "/items/42",
        "route": "/items/{item_id}",
        "status": 200,
    }


async def test_requests_are_counted_per_route_template(
    observed_client: AsyncClient, metric_delta: Callable[..., Callable[[], float]]
) -> None:
    handled = metric_delta(
        "http_requests_total", method="GET", route="/items/{item_id}", status="200"
    )

    await observed_client.get("/items/1")
    await observed_client.get("/items/2")

    assert handled() == 2


async def test_unknown_paths_share_one_label(
    observed_client: AsyncClient, metric_delta: Callable[..., Callable[[], float]]
) -> None:
    unmatched = metric_delta("http_requests_total", method="GET", route="unmatched", status="404")

    await observed_client.get("/random/path/123")

    assert unmatched() == 1


async def test_unhandled_errors_are_counted_and_logged_with_the_traceback(
    observed_client: AsyncClient,
    metric_delta: Callable[..., Callable[[], float]],
    caplog: pytest.LogCaptureFixture,
) -> None:
    failed = metric_delta("http_requests_total", method="GET", route="/crash", status="500")

    with caplog.at_level(logging.ERROR, logger="podcast_service.access"):
        response = await observed_client.get("/crash")

    [record] = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert (response.status_code, failed(), record.exc_info is not None) == (500, 1, True)
