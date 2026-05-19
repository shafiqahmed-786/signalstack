from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.db.organization import Organization
    from app.models.db.user import User


class WatchlistItem(Base, TimestampMixin):
    """
    Per-user company watchlist, scoped to organization.

    Unique on (organization_id, user_id, ticker) — a user cannot add
    the same ticker twice. Different users in the same org maintain
    separate watchlists.
    """

    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            "ticker",
            name="uq_watchlist_org_user_ticker",
        ),
        Index("ix_watchlist_org_user", "organization_id", "user_id"),
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
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ──────────────────────────────────────────
    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="watchlist_items",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<WatchlistItem ticker={self.ticker!r} user={self.user_id}>"