from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.db.member import OrganizationMember
from app.models.db.organization import Organization
from app.repositories.base import BaseRepository

log = structlog.get_logger(__name__)


class OrganizationRepository(BaseRepository):
    """
    Database operations for Organization and OrganizationMember models.

    Not tenant-aware at the repository level because org creation and
    lookup must happen before we know the tenant context.
    """

    # ── Organization queries ───────────────────────────────────

    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        result = await self._session.execute(
            select(Organization).where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_by_clerk_org_id(self, clerk_org_id: str) -> Organization | None:
        result = await self._session.execute(
            select(Organization).where(Organization.clerk_org_id == clerk_org_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self._session.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        slug: str,
        clerk_org_id: str | None = None,
        plan: str = "free",
    ) -> Organization:
        org = Organization(
            name=name,
            slug=slug,
            clerk_org_id=clerk_org_id,
            plan=plan,
            settings={},
        )
        self._session.add(org)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            log.warning(
                "org_repository.create_conflict",
                slug=slug,
                clerk_org_id=clerk_org_id,
                error=str(exc),
            )
            raise
        log.info(
            "org_repository.created",
            org_id=str(org.id),
            slug=slug,
            clerk_org_id=clerk_org_id,
        )
        return org

    async def upsert_from_clerk(
        self,
        clerk_org_id: str,
        name: str,
        slug: str,
    ) -> tuple[Organization, bool]:
        """
        Create or update an org from Clerk webhook data.
        Returns (org, created).
        """
        org = await self.get_by_clerk_org_id(clerk_org_id)
        if org is not None:
            org.name = name
            org.slug = slug
            await self._session.flush()
            return org, False
        org = await self.create(name=name, slug=slug, clerk_org_id=clerk_org_id)
        return org, True

    # ── Membership queries ─────────────────────────────────────

    async def get_member(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> OrganizationMember | None:
        result = await self._session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_member_by_clerk_ids(
        self,
        clerk_org_id: str,
        clerk_user_id: str,
    ) -> tuple[Organization, OrganizationMember] | None:
        """
        Resolve org + membership from Clerk IDs in a single joined query.
        Used by the tenant resolution dependency on every authenticated request.
        """
        from app.models.db.user import User  # Avoid circular import at module level

        result = await self._session.execute(
            select(Organization, OrganizationMember)
            .join(
                OrganizationMember,
                OrganizationMember.organization_id == Organization.id,
            )
            .join(User, User.id == OrganizationMember.user_id)
            .where(
                Organization.clerk_org_id == clerk_org_id,
                User.clerk_id == clerk_user_id,
            )
        )
        row = result.first()
        if row is None:
            return None
        return row[0], row[1]

    async def add_member(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        invited_by: uuid.UUID | None = None,
    ) -> OrganizationMember:
        member = OrganizationMember(
            organization_id=org_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by,
        )
        self._session.add(member)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            log.warning(
                "org_repository.add_member_conflict",
                org_id=str(org_id),
                user_id=str(user_id),
                error=str(exc),
            )
            raise
        log.info(
            "org_repository.member_added",
            org_id=str(org_id),
            user_id=str(user_id),
            role=role,
        )
        return member

    async def update_member_role(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        new_role: str,
    ) -> OrganizationMember | None:
        member = await self.get_member(org_id, user_id)
        if member is None:
            return None
        old_role = member.role
        member.role = new_role
        await self._session.flush()
        log.info(
            "org_repository.member_role_changed",
            org_id=str(org_id),
            user_id=str(user_id),
            old_role=old_role,
            new_role=new_role,
        )
        return member

    async def remove_member(
        self,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        member = await self.get_member(org_id, user_id)
        if member is None:
            return False
        await self._session.delete(member)
        await self._session.flush()
        log.info(
            "org_repository.member_removed",
            org_id=str(org_id),
            user_id=str(user_id),
        )
        return True

    async def list_members(self, org_id: uuid.UUID) -> list[OrganizationMember]:
        from app.models.db.user import User  # Avoid circular import at module level

        result = await self._session.execute(
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == org_id)
            .order_by(OrganizationMember.joined_at)
        )
        return list(result.scalars().all())