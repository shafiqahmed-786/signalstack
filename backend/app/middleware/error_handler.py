from __future__ import annotations

import structlog
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

log = structlog.get_logger(__name__)


def _error_body(code: str, message: str, details: object = None) -> dict:
    body: dict = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if details is not None:
        body["error"]["details"] = details
    return body


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle FastAPI/Starlette HTTPException.

    exc.detail can be a string (legacy FastAPI) or a structured dict
    from our own raise sites. We normalise both into our error envelope.
    """
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "HTTP_ERROR")
        message = exc.detail.get("message", str(exc.detail))
    else:
        code = "HTTP_ERROR"
        message = str(exc.detail) if exc.detail else "An error occurred"

    log.warning(
        "http.exception",
        status_code=exc.status_code,
        code=code,
        message=message,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(code, message),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handle Pydantic v2 request validation errors (422 Unprocessable Entity).

    Returns a structured list of field-level errors so the frontend can
    highlight specific form fields.
    """
    errors = [
        {
            "field": ".".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in exc.errors()
    ]

    log.info(
        "http.validation_error",
        path=request.url.path,
        error_count=len(errors),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_error_body(
            "VALIDATION_ERROR",
            "Request validation failed. Check the 'details' field for field-level errors.",
            details=errors,
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unexpected exceptions.

    Logs the full traceback (structlog will include exc_info).
    Returns a generic 500 response — never leaks internal details to the client.
    """
    log.error(
        "http.unhandled_exception",
        path=request.url.path,
        exc_type=type(exc).__name__,
        exc_msg=str(exc),
        exc_info=True,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_body(
            "INTERNAL_SERVER_ERROR",
            "An unexpected error occurred. The error has been logged.",
        ),
    )