from __future__ import annotations

import uuid
from abc import ABC

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain.tenant import TenantContext

log = structlog.get_logger(__name__)


class BaseRepository(ABC):
    """
    Abstract base for all repositories.

    Repositories own ALL database queries.
    No other layer (routes, services, middleware) touches the session directly.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session


class TenantAwareRepository(BaseRepository):
    """
    Base for repositories that operate on tenant-scoped data.

    Every public method accepts a TenantContext as its first argument.
    The _require_tenant helper asserts the context is present and logs
    the org_id into the structlog context for the duration of the call.

    Subclasses MUST apply the tenant filter to every query.
    The convention is to use _apply_tenant_filter as the last WHERE clause.
    """

    def _require_tenant(self, ctx: TenantContext) -> uuid.UUID:
        """
        Returns the org UUID from context, binding it to structlog.
        Raises AssertionError if context is somehow None (programming error).
        """
        assert ctx is not None, "TenantContext must not be None"
        log.debug(
            "repository.tenant_resolved",
            org_id=str(ctx.org_id),
            user_id=str(ctx.user_id),
        )
        return ctx.org_id

    def _org_filter(self, model_class: type, ctx: TenantContext):
        """
        Returns a SQLAlchemy WHERE clause: model_class.organization_id == ctx.org_id
        Use this in every query on tenant-scoped models.

        Example:
            stmt = select(ResearchReport).where(
                self._org_filter(ResearchReport, ctx),
                ResearchReport.is_archived.is_(False),
            )
        """
        return model_class.organization_id == ctx.org_id