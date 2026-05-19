from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.db.base import Base

if TYPE_CHECKING:
    from app.models.db.report import ResearchReport


class ReportSource(Base):
    """
    Source attribution record for every data point in a report.

    Each data point in the report JSON references a source_id that
    maps back to a row in this table. This is the citation registry.
    """

    __tablename__ = "report_sources"
    __table_args__ = (
        CheckConstraint(
            "source_type IN ('market_api','news_api','vector_db','filing')",
            name="ck_source_type",
        ),
        Index("ix_sources_report_id", "report_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("research_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
    # tool_name, ticker, article_id, chunk_id, doc_title, etc.
    # Note: renamed from 'metadata' which is reserved in SQLAlchemy Declarative API
    source_attributes: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )

    # ── Relationships ──────────────────────────────────────────
    report: Mapped[ResearchReport] = relationship(
        "ResearchReport",
        back_populates="sources",
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<ReportSource id={self.id} type={self.source_type!r} name={self.source_name!r}>"