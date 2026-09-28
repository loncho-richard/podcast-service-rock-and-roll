import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Literal

# asyncio tasks and `to_thread` copy the context, so enrichment logs keep the request id.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

LogFormat = Literal["json", "text"]

_TEXT_FORMAT = "%(asctime)s %(levelname)-7s [%(request_id)s] %(name)s: %(message)s"
_RECORD_ATTRIBUTES = frozenset(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {
    "message",
    "asctime",
    "request_id",
    "color_message",  # uvicorn's ANSI-colored copy of the message
}


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", "-")
        if request_id != "-":
            payload["request_id"] = request_id
        payload.update(
            (key, value)
            for key, value in vars(record).items()
            if key not in _RECORD_ATTRIBUTES and not key.startswith("_")
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


class _ServiceHandler(logging.StreamHandler):  # type: ignore[type-arg]
    """Marks the handler we install, so reconfiguring replaces only our own."""


def configure_logging(level: str, log_format: LogFormat) -> None:
    handler = _ServiceHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        JsonFormatter() if log_format == "json" else logging.Formatter(_TEXT_FORMAT)
    )

    root = logging.getLogger()
    for existing in [h for h in root.handlers if isinstance(h, _ServiceHandler)]:
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)

    for name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True
    # Superseded by our access log, which has the request id.
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("httpx").setLevel(logging.WARNING)
