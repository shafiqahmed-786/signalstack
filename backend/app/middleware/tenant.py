from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.tenant import TenantContext
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.security.clerk import ClerkClaims

log = structlog.get_logger(__name__)


async def resolve_tenant_context(
    claims: ClerkClaims,
    session: AsyncSession,
) -> TenantContext:
    """
    Resolve the full TenantContext from validated Clerk claims.

    Performs:
      1. User lookup by Clerk user ID
      2. Organization + membership lookup when org context exists

    In development mode, if no Clerk organization is selected,
    a temporary fallback TenantContext is returned so the frontend
    can function without multi-tenant setup.

    Raises ValueError for real resolution failures.
    """

    user_repo = UserRepository(session)
    org_repo = OrganizationRepository(session)

    # ── Resolve user first ─────────────────────────────────────
    user = await user_repo.get_by_clerk_id(claims.user_id)

    if user is None:
        raise ValueError(
            f"User with Clerk ID '{claims.user_id}' not found in database. "
            "The user.created webhook may not have been processed yet."
        )

    # ── Development fallback: no org selected ─────────────────
    if not claims.org_id:
        log.warning(
            "tenant.dev_bypass",
            message="No Clerk org found — using development org fallback",
            clerk_user_id=claims.user_id,
        )

        ctx = TenantContext(
            user_id=user.id,
            clerk_user_id=claims.user_id,
            org_id=None,
            clerk_org_id="dev-org",
            role="admin",
            email=user.email,
        )

        structlog.contextvars.bind_contextvars(
            org_id="dev-org",
            user_id=str(user.id),
            role="admin",
        )

        return ctx

    # ── Resolve org + membership ──────────────────────────────
    result = await org_repo.get_member_by_clerk_ids(
        clerk_org_id=claims.org_id,
        clerk_user_id=claims.user_id,
    )

    if result is None:
        raise ValueError(
            f"No membership found for user '{claims.user_id}' "
            f"in organization '{claims.org_id}'. "
            "The organizationMembership.created webhook may not have been processed."
        )

    org, member = result

    ctx = TenantContext(
        user_id=user.id,
        clerk_user_id=claims.user_id,
        org_id=org.id,
        clerk_org_id=claims.org_id,
        role=member.role,
        email=user.email,
    )

    structlog.contextvars.bind_contextvars(
        org_id=str(org.id),
        user_id=str(user.id),
        role=member.role,
    )

    return ctx