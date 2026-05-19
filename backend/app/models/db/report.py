from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.db.organization import Organization
    from app.models.db.source import ReportSource
    from app.models.db.user import User


class ResearchReport(Base, TimestampMixin):
    """
    Core tenant-scoped entity: one row per AI research query.

    report_data holds the full structured ResearchReport JSON blob.
    Stored as JSONB for schema flexibility as the output format evolves.
    """

    __tablename__ = "research_reports"
    __table_args__ = (
        CheckConstraint(
            "status IN ('created','planning','dispatching','synthesizing','completed','partial','failed','cancelled')",
            name="ck_report_status",
        ),
        # Primary access pattern: list by org, newest first
        Index("ix_reports_org_created", "organization_id", "created_at"),
        # Filter by status within an org
        Index("ix_reports_org_status", "organization_id", "status"),
        # GIN indexes for array columns (WHERE 'NVDA' = ANY(companies))
        Index("ix_reports_companies", "companies", postgresql_using="gin"),
        Index("ix_reports_tags", "tags", postgresql_using="gin"),
        # Full-text search across query + title
        Index(
            "ix_reports_fts",
            "organization_id",
            postgresql_using="gin",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # ── Tenant scope ───────────────────────────────────────────
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )

    # ── Query metadata ─────────────────────────────────────────
    query: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Ticker symbols extracted from the query + plan
    companies: Mapped[list[str]] = mapped_column(
        ARRAY(String()),
        nullable=False,
        default=list,
        server_default="ARRAY[]::varchar[]",
    )

    # ── Lifecycle ──────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="created",
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── AI Output ─────────────────────────────────────────────
    # Full structured ResearchReport JSON — see models/domain/research.py for schema
    report_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Generation provenance — stored separately for auditability
    generation_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── User organisation ──────────────────────────────────────
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(String()),
        nullable=False,
        default=list,
        server_default="ARRAY[]::varchar[]",
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── Observability ──────────────────────────────────────────
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tools_called: Mapped[list[str]] = mapped_column(
        ARRAY(String()),
        nullable=False,
        default=list,
        server_default="ARRAY[]::varchar[]",
    )
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── Relationships ──────────────────────────────────────────
    organization: Mapped[Organization] = relationship(
        "Organization",
        back_populates="reports",
        lazy="raise",
    )
    sources: Mapped[list[ReportSource]] = relationship(
        "ReportSource",
        back_populates="report",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<ResearchReport id={self.id} status={self.status!r}>"