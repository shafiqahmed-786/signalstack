from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.db.user import User
from app.repositories.base import BaseRepository

log = structlog.get_logger(__name__)


class UserRepository(BaseRepository):
    """
    All database operations for the User model.

    This repository is NOT tenant-aware — users exist globally.
    Tenant scoping for user data is enforced at the OrganizationMember level.
    """

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_clerk_id(self, clerk_id: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.clerk_id == clerk_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        clerk_id: str,
        email: str,
        full_name: str | None = None,
        avatar_url: str | None = None,
    ) -> User:
        user = User(
            clerk_id=clerk_id,
            email=email.lower(),
            full_name=full_name,
            avatar_url=avatar_url,
        )
        self._session.add(user)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            log.warning(
                "user_repository.create_conflict",
                clerk_id=clerk_id,
                email=email,
                error=str(exc),
            )
            raise
        log.info(
            "user_repository.created",
            user_id=str(user.id),
            clerk_id=clerk_id,
            email=email,
        )
        return user

    async def upsert_from_clerk(
        self,
        clerk_id: str,
        email: str,
        full_name: str | None = None,
        avatar_url: str | None = None,
    ) -> tuple[User, bool]:
        """
        Create or update a user record from Clerk webhook data.

        Returns (user, created) where created=True if the record is new.
        """
        user = await self.get_by_clerk_id(clerk_id)

        if user is not None:
            # Update mutable fields (email can change in Clerk)
            user.email = email.lower()
            user.full_name = full_name
            user.avatar_url = avatar_url
            await self._session.flush()
            log.info(
                "user_repository.updated",
                user_id=str(user.id),
                clerk_id=clerk_id,
            )
            return user, False

        user = await self.create(
            clerk_id=clerk_id,
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
        )
        return user, True