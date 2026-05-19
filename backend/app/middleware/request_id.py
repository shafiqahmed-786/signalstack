from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Outermost middleware — runs first on every request.

    Responsibilities:
      1. Extract or generate the X-Request-ID header
      2. Bind request_id to structlog's context variables so every
         log statement in this request automatically includes it
      3. Echo the request_id back in the response header
      4. Log the incoming request (method, path) and response (status, duration)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        import time

        # Honour an X-Request-ID header from an upstream proxy; generate otherwise
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Clear any leftover context from a previous request on this worker
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.monotonic()
        log.info(
            "http.request_received",
            method=request.method,
            path=request.url.path,
        )

        response: Response = await call_next(request)

        duration_ms = round((time.monotonic() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        log.info(
            "http.request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response