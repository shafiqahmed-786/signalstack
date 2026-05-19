from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.db.member import OrganizationMember


class User(Base, TimestampMixin):
    """
    Application user, synced from Clerk via webhook.

    clerk_id is the authoritative identifier from Clerk (e.g., "user_2abc...").
    We maintain our own UUID primary key for FK references.
    """

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_clerk_id", "clerk_id", unique=True),
        Index("ix_users_email", "email", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Clerk's user ID. Must be set for all real users; nullable only for tests.
    clerk_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────
    memberships: Mapped[list[OrganizationMember]] = relationship(
        "OrganizationMember",
        back_populates="user",
        foreign_keys="OrganizationMember.user_id",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"