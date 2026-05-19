from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    SQLAlchemy declarative base.

    All ORM models inherit from this.
    Imported by Alembic env.py for autogeneration.
    """

    pass


class TimestampMixin:
    """
    Mixin that adds created_at and updated_at columns to any model.

    Both columns use server-side defaults so they're set even when
    bypassing the ORM (e.g., raw SQL inserts in tests or migrations).
    """

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
        doc="UTC timestamp when the record was created.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="UTC timestamp when the record was last updated.",
    )