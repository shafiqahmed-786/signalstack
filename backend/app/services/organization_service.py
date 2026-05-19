from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository

log = structlog.get_logger(__name__)


class OrganizationService:
    """
    Handles Clerk webhook events that affect org/user data in our database.

    Each method corresponds to one Clerk webhook event type.
    The service orchestrates repositories; all DB access goes through them.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._user_repo = UserRepository(session)
        self._org_repo = OrganizationRepository(session)

    async def handle_user_created(self, data: dict) -> None:
        """
        Event: user.created

        Clerk payload data fields used:
          id                         → clerk_id
          email_addresses[]          → find primary email
          primary_email_address_id   → which email is primary
          first_name, last_name      → full_name
          image_url                  → avatar_url
        """
        clerk_id: str = data["id"]
        primary_email_id: str | None = data.get("primary_email_address_id")
        emails: list[dict] = data.get("email_addresses", [])

        email = ""
        for e in emails:
            if e.get("id") == primary_email_id:
                email = e.get("email_address", "")
                break
        if not email and emails:
            email = emails[0].get("email_address", "")

        first = data.get("first_name") or ""
        last = data.get("last_name") or ""
        full_name = f"{first} {last}".strip() or None
        avatar_url: str | None = data.get("image_url")

        user, created = await self._user_repo.upsert_from_clerk(
            clerk_id=clerk_id,
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
        )

        log.info(
            "org_service.user_synced",
            clerk_id=clerk_id,
            user_id=str(user.id),
            created=created,
        )

    async def handle_user_updated(self, data: dict) -> None:
        """Event: user.updated — same sync logic as user.created."""
        await self.handle_user_created(data)

    async def handle_organization_created(self, data: dict) -> None:
        """
        Event: organization.created

        Clerk payload data fields used:
          id     → clerk_org_id
          name   → name
          slug   → slug
        """
        clerk_org_id: str = data["id"]
        name: str = data.get("name", "Unnamed Organization")
        slug: str = data.get("slug", clerk_org_id)

        org, created = await self._org_repo.upsert_from_clerk(
            clerk_org_id=clerk_org_id,
            name=name,
            slug=slug,
        )

        log.info(
            "org_service.org_synced",
            clerk_org_id=clerk_org_id,
            org_id=str(org.id),
            created=created,
        )

    async def handle_organization_updated(self, data: dict) -> None:
        """Event: organization.updated — same sync as organization.created."""
        await self.handle_organization_created(data)

    async def handle_membership_created(self, data: dict) -> None:
        """
        Event: organizationMembership.created

        Clerk payload data fields used:
          organization.id              → clerk_org_id
          public_user_data.user_id     → clerk_user_id
          role                         → "org:admin" | "org:member"
        """
        from app.security.clerk import CLERK_ROLE_MAP

        clerk_org_id: str = data["organization"]["id"]
        clerk_user_id: str = data["public_user_data"]["user_id"]
        clerk_role: str = data.get("role", "org:member")
        internal_role = CLERK_ROLE_MAP.get(clerk_role, "analyst")

        org = await self._org_repo.get_by_clerk_org_id(clerk_org_id)
        if org is None:
            log.warning(
                "org_service.membership_org_not_found",
                clerk_org_id=clerk_org_id,
                clerk_user_id=clerk_user_id,
            )
            return

        user = await self._user_repo.get_by_clerk_id(clerk_user_id)
        if user is None:
            log.warning(
                "org_service.membership_user_not_found",
                clerk_org_id=clerk_org_id,
                clerk_user_id=clerk_user_id,
            )
            return

        existing = await self._org_repo.get_member(org.id, user.id)
        if existing is not None:
            # Update role if it changed
            if existing.role != internal_role:
                await self._org_repo.update_member_role(org.id, user.id, internal_role)
        else:
            await self._org_repo.add_member(
                org_id=org.id,
                user_id=user.id,
                role=internal_role,
            )

        log.info(
            "org_service.membership_synced",
            org_id=str(org.id),
            user_id=str(user.id),
            role=internal_role,
        )

    async def handle_membership_updated(self, data: dict) -> None:
        """Event: organizationMembership.updated — same sync as created."""
        await self.handle_membership_created(data)

    async def handle_membership_deleted(self, data: dict) -> None:
        """
        Event: organizationMembership.deleted

        Removes the membership record. The user and org records are retained.
        """
        clerk_org_id: str = data["organization"]["id"]
        clerk_user_id: str = data["public_user_data"]["user_id"]

        org = await self._org_repo.get_by_clerk_org_id(clerk_org_id)
        if org is None:
            return

        user = await self._user_repo.get_by_clerk_id(clerk_user_id)
        if user is None:
            return

        removed = await self._org_repo.remove_member(org.id, user.id)
        log.info(
            "org_service.membership_removed",
            org_id=str(org.id),
            user_id=str(user.id),
            removed=removed,
        )