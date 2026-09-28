import json
import logging
from collections.abc import Callable

import pytest

from podcast_service.infrastructure.observability import JsonFormatter, configure_logging


@pytest.mark.usefixtures("within_request")
def test_json_line_carries_request_id_and_extra_fields(
    json_formatter: JsonFormatter, make_record: Callable[..., logging.LogRecord]
) -> None:
    record = make_record("Fetched %d podcasts", 3, ingestion={"source": "live"})

    line = json.loads(json_formatter.format(record))

    assert {key: value for key, value in line.items() if key != "timestamp"} == {
        "level": "INFO",
        "logger": "podcast_service.test",
        "message": "Fetched 3 podcasts",
        "request_id": "req-123",
        "ingestion": {"source": "live"},
    }


def test_json_line_outside_a_request_has_no_request_id(
    json_formatter: JsonFormatter, make_record: Callable[..., logging.LogRecord]
) -> None:
    line = json.loads(json_formatter.format(make_record("Starting up")))

    assert "request_id" not in line


def test_uvicorn_colored_duplicate_of_the_message_is_dropped(
    json_formatter: JsonFormatter, make_record: Callable[..., logging.LogRecord]
) -> None:
    record = make_record("Uvicorn running", color_message="\x1b[1mUvicorn running\x1b[0m")

    assert "color_message" not in json.loads(json_formatter.format(record))


def test_json_line_includes_the_traceback(
    json_formatter: JsonFormatter, make_record: Callable[..., logging.LogRecord]
) -> None:
    line = json.loads(json_formatter.format(make_record("Failed", exc_info=True)))

    assert "ValueError: boom" in line["exception"]


@pytest.mark.usefixtures("restore_logging")
def test_configuring_twice_keeps_a_single_service_handler() -> None:
    configure_logging("INFO", "json")

    configure_logging("DEBUG", "text")

    root = logging.getLogger()
    service_handlers = [h for h in root.handlers if type(h).__name__ == "_ServiceHandler"]
    assert (len(service_handlers), root.level) == (1, logging.DEBUG)


@pytest.mark.usefixtures("restore_logging")
def test_noisy_loggers_are_quieted() -> None:
    configure_logging("INFO", "json")

    assert (
        logging.getLogger("uvicorn.access").disabled,
        logging.getLogger("httpx").level,
    ) == (True, logging.WARNING)
