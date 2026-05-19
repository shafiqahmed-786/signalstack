from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.db.audit import AuditLog
    from app.models.db.cache import QueryCache
    from app.models.db.member import OrganizationMember
    from app.models.db.report import ResearchReport
    from app.models.db.watchlist import WatchlistItem


class Organization(Base, TimestampMixin):
    """
    Tenant root entity.

    Every multi-tenant table carries organization_id as a FK to this table.
    clerk_org_id is nullable to allow seeding without a real Clerk instance.
    """

    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint("plan IN ('free', 'pro', 'enterprise')", name="ck_org_plan"),
        Index("ix_organizations_clerk_org_id", "clerk_org_id"),
        Index("ix_organizations_slug", "slug"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # Clerk's organization ID (e.g., "org_2abc..."). Nullable for seeded/demo orgs.
    clerk_org_id: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    # Flexible JSON settings: token limits, feature flags, etc.
    settings: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # ── Relationships ──────────────────────────────────────────
    members: Mapped[list[OrganizationMember]] = relationship(
        "OrganizationMember",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="raise",  # Explicit: never allow implicit lazy loading
    )
    reports: Mapped[list[ResearchReport]] = relationship(
        "ResearchReport",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    watchlist_items: Mapped[list[WatchlistItem]] = relationship(
        "WatchlistItem",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        "AuditLog",
        back_populates="organization",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id} slug={self.slug!r}>"