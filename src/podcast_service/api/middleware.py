import logging
import re
import time
import uuid

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from podcast_service.infrastructure.observability import (
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS,
    request_id_var,
)

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

access_logger = logging.getLogger("podcast_service.access")


class RequestContextMiddleware:
    """Request id, access log and HTTP metrics for every request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _incoming_request_id(scope) or uuid.uuid4().hex
        token = request_id_var.set(request_id)
        status = 500  # unless the app manages to send a response
        started = time.perf_counter()

        async def send_with_request_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message).append(REQUEST_ID_HEADER, request_id)
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            access_logger.exception("Unhandled error")
            raise
        finally:
            duration = time.perf_counter() - started
            route = getattr(scope.get("route"), "path", None) or "unmatched"
            method = scope["method"]
            HTTP_REQUESTS.labels(method, route, str(status)).inc()
            HTTP_REQUEST_DURATION.labels(method, route).observe(duration)
            access_logger.info(
                "%s %s %d",
                method,
                scope["path"],
                status,
                extra={
                    "method": method,
                    "path": scope["path"],
                    "route": route,
                    "status": status,
                    "duration_ms": round(duration * 1000, 1),
                },
            )
            request_id_var.reset(token)


def _incoming_request_id(scope: Scope) -> str | None:
    for name, value in scope["headers"]:
        if name == b"x-request-id":
            candidate = value.decode("latin-1")
            return candidate if _VALID_REQUEST_ID.match(candidate) else None
    return None
