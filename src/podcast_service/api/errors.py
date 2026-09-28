from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from podcast_service.api.schemas import ErrorDetail, ErrorResponse
from podcast_service.application.auth import AuthenticationError
from podcast_service.domain.ingestion import PodcastRejectedError, SourceUnavailableError
from podcast_service.domain.shared import DomainError, NotFoundError

_DOMAIN_STATUS: dict[type[DomainError], int] = {
    AuthenticationError: HTTPStatus.UNAUTHORIZED,
    NotFoundError: HTTPStatus.NOT_FOUND,
    PodcastRejectedError: HTTPStatus.UNPROCESSABLE_ENTITY,
    SourceUnavailableError: HTTPStatus.SERVICE_UNAVAILABLE,
}

_HTTP_CODES: dict[int, str] = {
    HTTPStatus.BAD_REQUEST: "bad_request",
    HTTPStatus.UNAUTHORIZED: "unauthorized",
    HTTPStatus.FORBIDDEN: "forbidden",
    HTTPStatus.NOT_FOUND: "not_found",
    HTTPStatus.METHOD_NOT_ALLOWED: "method_not_allowed",
    HTTPStatus.SERVICE_UNAVAILABLE: "service_unavailable",
}

_ERROR_DESCRIPTIONS: dict[int, str] = {
    HTTPStatus.UNAUTHORIZED: "Missing, invalid or expired credentials.",
    HTTPStatus.NOT_FOUND: "The resource does not exist.",
    HTTPStatus.UNPROCESSABLE_ENTITY: "Invalid request, or a rejected podcast.",
    HTTPStatus.INTERNAL_SERVER_ERROR: "Unexpected error.",
    HTTPStatus.SERVICE_UNAVAILABLE: "The source is unavailable.",
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses` for the given error codes, all using the shared error shape."""
    return {
        int(status): {"model": ErrorResponse, "description": _ERROR_DESCRIPTIONS[status]}
        for status in status_codes
    }


# Every protected route can fail with these.
COMMON_ERRORS = error_responses(
    HTTPStatus.UNAUTHORIZED, HTTPStatus.UNPROCESSABLE_ENTITY, HTTPStatus.INTERNAL_SERVER_ERROR
)


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message, details=details))
    return JSONResponse(
        status_code=int(status_code),
        content=body.model_dump(mode="json"),
        headers=headers,
    )


async def _handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    status_code = next(
        (status for cls, status in _DOMAIN_STATUS.items() if isinstance(exc, cls)),
        HTTPStatus.UNPROCESSABLE_ENTITY,
    )
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, AuthenticationError) else None
    return error_response(status_code, exc.code, exc.message, headers=headers)


async def _handle_http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    return error_response(
        exc.status_code,
        _HTTP_CODES.get(exc.status_code, "http_error"),
        str(exc.detail),
        headers=exc.headers,
    )


async def _handle_validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Only expose location/message/type; the raw input may be large or sensitive.
    details = [
        {"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]} for err in exc.errors()
    ]
    return error_response(
        HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", "Invalid request.", details
    )


async def _handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    return error_response(
        HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error", "An unexpected error occurred."
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle_domain_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(Exception, _handle_unexpected_error)
