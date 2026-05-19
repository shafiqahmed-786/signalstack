from __future__ import annotations

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.security.clerk import ClerkClaims, get_clerk_verifier

log = structlog.get_logger(__name__)


class ClerkAuthMiddleware(BaseHTTPMiddleware):
    """
    JWT verification middleware — runs after RequestIDMiddleware.

    Responsibilities:
      - Extract the Bearer token from the Authorization header
      - Verify the JWT signature using ClerkJWTVerifier (JWKS-backed)
      - Set request.state.clerk_claims to ClerkClaims on success, None otherwise

    This middleware NEVER rejects requests — it only sets or clears the
    claims object. Routes that require authentication use the
    get_current_claims() FastAPI dependency, which raises 401 when claims
    are None.

    This design keeps auth enforcement at the route/dependency layer, not
    the middleware layer, and allows public routes (e.g., /health) to
    work without any Authorization header.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.clerk_claims = None  # Default: unauthenticated

        auth_header = request.headers.get("Authorization", "")

        if auth_header.startswith("Bearer "):
            token = auth_header.removeprefix("Bearer ").strip()
            if token:
                try:
                    verifier = get_clerk_verifier()
                    claims: ClerkClaims = verifier.verify(token)
                    request.state.clerk_claims = claims
                    # Bind to structlog so auth context appears in all downstream logs
                    structlog.contextvars.bind_contextvars(
                        clerk_user_id=claims.user_id,
                        clerk_org_id=claims.org_id,
                    )
                except ValueError as exc:
                    # Invalid or expired token — treat as unauthenticated
                    # The route will decide whether to reject or allow
                    log.debug(
                        "clerk.jwt_invalid",
                        reason=str(exc),
                        path=request.url.path,
                    )

        return await call_next(request)