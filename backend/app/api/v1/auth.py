from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_tenant_ctx
from app.db.session import get_db
from app.models.domain.tenant import TenantContext
from app.models.schemas.responses.auth import (
    OrganizationResponse,
    UserMeResponse,
    WebhookAckResponse,
)
from app.repositories.organization_repository import OrganizationRepository
from app.security.clerk import verify_webhook_signature
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/auth", tags=["Authentication"])
log = structlog.get_logger(__name__)


@router.get(
    "/me",
    response_model=UserMeResponse,
    summary="Get current user",
    description=(
        "Returns the authenticated user's profile and resolved organization context. "
        "This endpoint is the frontend's primary source for the current role and org."
    ),
)
async def get_me(
    ctx: TenantContext = Depends(get_tenant_ctx),
    session: AsyncSession = Depends(get_db),
) -> UserMeResponse:
    org_repo = OrganizationRepository(session)
    org = await org_repo.get_by_id(ctx.org_id)

    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "ORGANIZATION_NOT_FOUND",
                "message": "The organization associated with this token no longer exists.",
            },
        )

    return UserMeResponse(
        user_id=str(ctx.user_id),
        email=ctx.email,
        full_name=None,     # Fetching full_name would require an extra user query;
        avatar_url=None,    # add a UserRepository.get_by_id call here if needed Day 4+
        organization=OrganizationResponse(
            id=str(org.id),
            name=org.name,
            slug=org.slug,
            plan=org.plan,
        ),
        role=ctx.role,
        is_admin=ctx.is_admin,
    )


@router.post(
    "/sync",
    response_model=WebhookAckResponse,
    summary="Clerk webhook sync",
    description=(
        "Receives Clerk webhook events and syncs user/org data to our database. "
        "Must be registered in the Clerk Dashboard under Webhooks. "
        "Validates the Svix signature before processing."
    ),
    status_code=status.HTTP_200_OK,
)
async def clerk_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> WebhookAckResponse:
    from app.config import get_settings

    settings = get_settings()

    # ── 1. Read raw body (must read before any parsing for signature check) ──
    payload_bytes = await request.body()

    # ── 2. Extract Svix signature headers ────────────────────────────────────
    svix_id = request.headers.get("svix-id", "")
    svix_timestamp = request.headers.get("svix-timestamp", "")
    svix_signature = request.headers.get("svix-signature", "")

    if not svix_id or not svix_timestamp or not svix_signature:
        log.warning(
            "webhook.missing_svix_headers",
            has_id=bool(svix_id),
            has_timestamp=bool(svix_timestamp),
            has_signature=bool(svix_signature),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "MISSING_WEBHOOK_HEADERS",
                "message": "Missing required Svix signature headers.",
            },
        )

    # ── 3. Verify signature ───────────────────────────────────────────────────
    if not verify_webhook_signature(
        payload_bytes=payload_bytes,
        svix_id=svix_id,
        svix_timestamp=svix_timestamp,
        svix_signature=svix_signature,
        webhook_secret=settings.clerk_webhook_secret,
    ):
        log.warning(
            "webhook.signature_invalid",
            svix_id=svix_id,
            path=str(request.url),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_WEBHOOK_SIGNATURE",
                "message": "Webhook signature verification failed.",
            },
        )

    # ── 4. Parse event ────────────────────────────────────────────────────────
    import json

    try:
        body = json.loads(payload_bytes)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_PAYLOAD",
                "message": f"Could not parse webhook payload as JSON: {exc}",
            },
        ) from exc

    event_type: str = body.get("type", "")
    event_data: dict = body.get("data", {})

    log.info("webhook.received", event_type=event_type, svix_id=svix_id)

    # ── 5. Dispatch to service ────────────────────────────────────────────────
    svc = OrganizationService(session)

    dispatch: dict[str, object] = {
        "user.created": svc.handle_user_created,
        "user.updated": svc.handle_user_updated,
        "organization.created": svc.handle_organization_created,
        "organization.updated": svc.handle_organization_updated,
        "organizationMembership.created": svc.handle_membership_created,
        "organizationMembership.updated": svc.handle_membership_updated,
        "organizationMembership.deleted": svc.handle_membership_deleted,
    }

    handler = dispatch.get(event_type)
    if handler is not None:
        await handler(event_data)  # type: ignore[operator]
        log.info("webhook.processed", event_type=event_type)
    else:
        # Unknown event types are acknowledged but not processed
        log.info("webhook.event_type_ignored", event_type=event_type)

    return WebhookAckResponse(received=True, event_type=event_type)