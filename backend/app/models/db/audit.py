from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db.base import Base

if TYPE_CHECKING:
    from app.models.db.organization import Organization


class AuditLog(Base):
    """
    Immutable audit trail for all data-modifying actions.

    action follows the format 'resource.verb':
      report.created, report.deleted, member.role_changed, watchlist.added

    request_id correlates with structured logs for full trace replay.
    before_state / after_state capture the diff for update operations.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_org_created", "organization_id", "created_at"),
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_user_id", "user_id"),
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
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="Null for system-generated events (e.g., webhook sync).",
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Format: resource.verb — e.g., 'report.created', 'member.role_changed'",
    )
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    before_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after_state: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Correlates with X-Request-ID header and structlog context
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ──────────────────────────────────────────
    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="audit_logs",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<AuditLog action={self.action!r} entity={self.entity_type}:{self.entity_id}>"