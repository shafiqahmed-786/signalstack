from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.db.organization import Organization
    from app.models.db.user import User


class OrganizationMember(Base, TimestampMixin):
    """
    RBAC junction table: user ↔ organization with role.

    Uniqueness constraint on (organization_id, user_id) ensures
    a user cannot have multiple roles in the same org simultaneously.
    Role changes must UPDATE the existing record.
    """

    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_member"),
        CheckConstraint("role IN ('admin', 'analyst')", name="ck_member_role"),
        Index("ix_org_members_org_id", "organization_id"),
        Index("ix_org_members_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        nullable=False,
        default="analyst",
        doc="'admin' has full org access; 'analyst' can create/view own research.",
    )
    # The user who sent the invite (nullable for the first admin / seeded members)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Relationships ──────────────────────────────────────────
    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="members",
        lazy="raise",
    )
    user: Mapped[User] = relationship(
        "User",
        back_populates="memberships",
        foreign_keys=[user_id],
        lazy="raise",
    )

    def __repr__(self) -> str:
        return (
            f"<OrganizationMember org={self.organization_id} "
            f"user={self.user_id} role={self.role!r}>"
        )