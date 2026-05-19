from __future__ import annotations

import structlog
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.middleware.tenant import resolve_tenant_context
from app.models.domain.tenant import TenantContext
from app.security.clerk import ClerkClaims

log = structlog.get_logger(__name__)


async def get_current_claims(request: Request) -> ClerkClaims:
    """
    FastAPI dependency: requires a valid Clerk JWT to have been verified
    by ClerkAuthMiddleware.

    Raises 401 if no valid claims are present on the request state.
    Use this dependency on any route that requires authentication.
    """
    claims: ClerkClaims | None = request.state.clerk_claims

    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "A valid Bearer token is required.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    return claims


async def get_tenant_ctx(
    claims: ClerkClaims = Depends(get_current_claims),
    session: AsyncSession = Depends(get_db),
) -> TenantContext:
    """
    FastAPI dependency: resolves the full TenantContext for the request.

    Combines ClerkClaims (from middleware) with DB lookups (user + org + member).
    Returns an immutable TenantContext that is safe to pass through the call stack.

    Raises:
      401 if no claims present (propagated from get_current_claims)
      403 if the user/org is not found in our DB
    """
    try:
        ctx = await resolve_tenant_context(claims=claims, session=session)
    except ValueError as exc:
        log.warning(
            "tenant.resolution_failed",
            clerk_user_id=claims.user_id,
            clerk_org_id=claims.org_id,
            reason=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "TENANT_RESOLUTION_FAILED",
                "message": str(exc),
            },
        ) from exc

    return ctx


def require_role(*allowed_roles: str):
    """
    Dependency factory for role-based access control.

    Usage:
        @router.delete("/{id}", dependencies=[Depends(require_role("admin"))])
        async def delete_report(...): ...

        # Or to receive the ctx:
        @router.get("/admin-only")
        async def admin_route(ctx: TenantContext = Depends(require_role("admin"))): ...
    """

    async def _checker(
        ctx: TenantContext = Depends(get_tenant_ctx),
    ) -> TenantContext:
        if ctx.role not in allowed_roles:
            log.warning(
                "rbac.access_denied",
                user_id=str(ctx.user_id),
                org_id=str(ctx.org_id),
                user_role=ctx.role,
                required_roles=allowed_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "INSUFFICIENT_PERMISSIONS",
                    "message": (
                        f"This action requires one of the following roles: "
                        f"{', '.join(allowed_roles)}. Your current role is '{ctx.role}'."
                    ),
                },
            )
        return ctx

    return _checker


# Convenience aliases — use these in route definitions
require_admin = require_role("admin")
require_analyst = require_role("admin", "analyst")