"""
Import all ORM models here so SQLAlchemy registers them with the
mapper before any engine or session is created.

This file MUST be imported by alembic/env.py for autogeneration to work.
Do not remove any import, even if the model appears unused.
"""

from app.models.db.audit import AuditLog
from app.models.db.base import Base, TimestampMixin
from app.models.db.cache import QueryCache
from app.models.db.member import OrganizationMember
from app.models.db.organization import Organization
from app.models.db.report import ResearchReport
from app.models.db.source import ReportSource
from app.models.db.user import User
from app.models.db.watchlist import WatchlistItem

__all__ = [
    "Base",
    "TimestampMixin",
    "Organization",
    "User",
    "OrganizationMember",
    "ResearchReport",
    "ReportSource",
    "WatchlistItem",
    "QueryCache",
    "AuditLog",
]