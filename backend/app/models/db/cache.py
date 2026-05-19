from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.db.base import Base


class QueryCache(Base):
    """
    Query-level result cache keyed by a SHA-256 hash.

    cache_key = SHA256(normalize(query) + sorted_tickers + date_bucket)

    This prevents calling the AI layer for the same query within the
    cache window. TTL is enforced at the application layer on read;
    a periodic cleanup job (or DB-level cron) deletes expired rows.
    """

    __tablename__ = "query_cache"
    __table_args__ = (
        Index("ix_cache_key", "cache_key", unique=True),
        Index("ix_cache_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    # SHA-256 hex digest of the normalized cache key
    cache_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    report_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    last_hit_at: Mapped[datetime | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<QueryCache key={self.cache_key[:16]}... expires={self.expires_at}>"