import logging
from collections.abc import Callable, Iterator

import pytest

from podcast_service.infrastructure.observability import (
    JsonFormatter,
    RequestIdFilter,
    request_id_var,
)


@pytest.fixture
def json_formatter() -> JsonFormatter:
    return JsonFormatter()


@pytest.fixture
def within_request() -> Iterator[str]:
    token = request_id_var.set("req-123")
    yield "req-123"
    request_id_var.reset(token)


@pytest.fixture
def make_record() -> Callable[..., logging.LogRecord]:
    def build(
        msg: str,
        *args: object,
        level: int = logging.INFO,
        exc_info: bool = False,
        **extra: object,
    ) -> logging.LogRecord:
        info = None
        if exc_info:
            try:
                raise ValueError("boom")
            except ValueError as exc:
                info = (type(exc), exc, exc.__traceback__)
        record = logging.getLogger("podcast_service.test").makeRecord(
            "podcast_service.test", level, __file__, 1, msg, args, info, extra=extra
        )
        RequestIdFilter().filter(record)
        return record

    return build


@pytest.fixture
def restore_logging() -> Iterator[None]:
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    access = logging.getLogger("uvicorn.access")
    yield
    root.handlers[:] = handlers
    root.setLevel(level)
    access.disabled = False
