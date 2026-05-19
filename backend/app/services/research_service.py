"""
app/services/research_service.py

Business logic layer for research operations.

Responsibilities:
  - Rate-limit enforcement (per-user sliding window)
  - Report record lifecycle management
  - Background orchestration launch via asyncio.create_task
  - CRUD delegation to ReportRepository
"""
from __future__ import annotations

import asyncio
import uuid

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.domain.tenant import TenantContext
from app.models.schemas.requests.research import ReportUpdateRequest, ResearchQueryRequest
from app.models.schemas.responses.research import (
    ReportListItemResponse,
    ReportListResponse,
    ReportStatusResponse,
    ResearchReportResponse,
)
from app.repositories.report_repository import ReportRepository

log = structlog.get_logger(__name__)
settings = get_settings()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _orm_to_list_item(orm: object) -> ReportListItemResponse:
    return ReportListItemResponse(
        id=str(orm.id),                         # type: ignore[attr-defined]
        query=orm.query,                         # type: ignore[attr-defined]
        title=orm.title,                         # type: ignore[attr-defined]
        status=orm.status,                       # type: ignore[attr-defined]
        companies=orm.companies or [],           # type: ignore[attr-defined]
        tags=orm.tags or [],                     # type: ignore[attr-defined]
        is_pinned=orm.is_pinned,                 # type: ignore[attr-defined]
        is_archived=orm.is_archived,             # type: ignore[attr-defined]
        cache_hit=orm.cache_hit,                 # type: ignore[attr-defined]
        processing_time_ms=orm.processing_time_ms,  # type: ignore[attr-defined]
        created_at=orm.created_at.isoformat(),   # type: ignore[attr-defined]
        updated_at=orm.updated_at.isoformat(),   # type: ignore[attr-defined]
    )


def _orm_to_detail(orm: object) -> ResearchReportResponse:
    return ResearchReportResponse(
        id=str(orm.id),                          # type: ignore[attr-defined]
        query=orm.query,                          # type: ignore[attr-defined]
        title=orm.title,                          # type: ignore[attr-defined]
        status=orm.status,                        # type: ignore[attr-defined]
        companies=orm.companies or [],            # type: ignore[attr-defined]
        tags=orm.tags or [],                      # type: ignore[attr-defined]
        is_pinned=orm.is_pinned,                  # type: ignore[attr-defined]
        is_archived=orm.is_archived,              # type: ignore[attr-defined]
        cache_hit=orm.cache_hit,                  # type: ignore[attr-defined]
        processing_time_ms=orm.processing_time_ms,   # type: ignore[attr-defined]
        total_tokens_used=orm.total_tokens_used,     # type: ignore[attr-defined]
        model_used=orm.model_used,                   # type: ignore[attr-defined]
        tools_called=orm.tools_called or [],         # type: ignore[attr-defined]
        created_at=orm.created_at.isoformat(),       # type: ignore[attr-defined]
        updated_at=orm.updated_at.isoformat(),       # type: ignore[attr-defined]
        report=orm.report_data,                      # type: ignore[attr-defined]
        error_message=orm.error_message,             # type: ignore[attr-defined]
    )


# ── Service ───────────────────────────────────────────────────────────────────


class RateLimitExceeded(Exception):
    def __init__(self, limit: int, window_hours: int) -> None:
        super().__init__(f"Rate limit: {limit} queries per {window_hours}h")
        self.limit = limit
        self.window_hours = window_hours


class ResearchService:
    """
    Facade for all research business operations.
    Instantiated per-request.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ReportRepository(session)

    # ── Query submission ───────────────────────────────────────────────────────

    async def submit_query(
        self,
        body: ResearchQueryRequest,
        ctx: TenantContext,
    ) -> tuple[uuid.UUID, asyncio.Queue]:
        """
        Validate, create the DB record, and launch the orchestration background task.
        Returns (report_id, sse_queue) — the queue is drained by the SSE endpoint.
        """
        # Rate limiting
        recent = await self._repo.count_recent_queries(
            org_id=ctx.org_id,
            user_id=ctx.user_id,
            hours=1,
        )
        if recent >= settings.rate_limit_research_per_hour:
            log.warning(
                "research_service.rate_limited",
                user_id=str(ctx.user_id),
                count=recent,
                limit=settings.rate_limit_research_per_hour,
            )
            raise RateLimitExceeded(settings.rate_limit_research_per_hour, 1)

        # Create initial DB record
        companies_hint = [c.upper() for c in (body.companies or [])]
        report_id = await self._repo.create(
            ctx=ctx,
            query=body.query,
            companies_hint=companies_hint,
        )
        await self._session.commit()

        log.info(
            "research_service.query_accepted",
            report_id=str(report_id),
            user_id=str(ctx.user_id),
            companies=companies_hint,
        )

        sse_queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        asyncio.create_task(
            _run_orchestration_bg(
                report_id=report_id,
                body=body,
                ctx=ctx,
                sse_queue=sse_queue,
            ),
            name=f"orch-{report_id}",
        )

        return report_id, sse_queue

    # ── CRUD ───────────────────────────────────────────────────────────────────

    async def get_report(
        self, report_id: uuid.UUID, ctx: TenantContext
    ) -> ResearchReportResponse:
        orm = await self._repo.get_by_id(report_id, ctx)
        if orm is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "REPORT_NOT_FOUND", "message": "Report not found."},
            )
        return _orm_to_detail(orm)

    async def get_report_status(
        self, report_id: uuid.UUID, ctx: TenantContext
    ) -> ReportStatusResponse:
        orm = await self._repo.get_by_id(report_id, ctx)
        if orm is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "REPORT_NOT_FOUND", "message": "Report not found."},
            )
        return ReportStatusResponse(
            report_id=str(orm.id),              # type: ignore[attr-defined]
            status=orm.status,                  # type: ignore[attr-defined]
            processing_time_ms=orm.processing_time_ms,  # type: ignore[attr-defined]
            created_at=orm.created_at.isoformat(),       # type: ignore[attr-defined]
            error_message=orm.error_message,             # type: ignore[attr-defined]
            companies=orm.companies or [],               # type: ignore[attr-defined]
        )

    async def list_reports(
        self,
        ctx: TenantContext,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
        companies_filter: list[str] | None = None,
        pinned_only: bool = False,
    ) -> ReportListResponse:
        rows, total = await self._repo.list_for_tenant(
            ctx=ctx,
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            companies_filter=companies_filter,
            pinned_only=pinned_only,
        )
        return ReportListResponse(
            reports=[_orm_to_list_item(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    async def update_report(
        self,
        report_id: uuid.UUID,
        updates: ReportUpdateRequest,
        ctx: TenantContext,
    ) -> ResearchReportResponse:
        updated = await self._repo.update_metadata(
            report_id=report_id,
            ctx=ctx,
            title=updates.title,
            tags=updates.tags,
            is_pinned=updates.is_pinned,
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "REPORT_NOT_FOUND", "message": "Report not found."},
            )
        return await self.get_report(report_id, ctx)

    async def archive_report(
        self, report_id: uuid.UUID, ctx: TenantContext
    ) -> None:
        archived = await self._repo.archive(report_id, ctx)
        if not archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "REPORT_NOT_FOUND", "message": "Report not found."},
            )
        log.info("research_service.report_archived",
                 report_id=str(report_id), user_id=str(ctx.user_id))


# ── Background orchestration task ─────────────────────────────────────────────


async def _run_orchestration_bg(
    report_id: uuid.UUID,
    body: ResearchQueryRequest,
    ctx: TenantContext,
    sse_queue: asyncio.Queue,
) -> None:
    """
    Runs in a separate asyncio Task with its own DB session.
    The request session is committed and idle by the time this task begins.
    """
    from app.db.session import AsyncSessionLocal
    from app.orchestration.state_machine import SSEEvent

    log.info("orchestration_bg.started", report_id=str(report_id))

    async with AsyncSessionLocal() as session:
        try:
            from app.orchestration.engine import OrchestrationEngine
            engine = OrchestrationEngine(session)
            await engine.run(
                report_id=report_id,
                body=body,
                ctx=ctx,
                sse_queue=sse_queue,
            )
        except ImportError as exc:
            log.warning("orchestration_bg.import_error", error=str(exc))
            from app.models.domain.research import ReportStatus
            from app.repositories.report_repository import ReportRepository
            repo = ReportRepository(session)
            try:
                await repo.update_status(
                    report_id=report_id,
                    status=ReportStatus.FAILED,
                    error_message="Orchestration engine unavailable",
                )
                await session.commit()
            except Exception:
                pass
            await sse_queue.put(SSEEvent(
                event="report.failed",
                data={
                    "report_id": str(report_id),
                    "status": "failed",
                    "error": "Orchestration engine unavailable",
                },
            ))
            await sse_queue.put(None)
        except Exception as exc:
            log.error("orchestration_bg.unhandled", report_id=str(report_id),
                      error=str(exc), exc_info=True)
            await sse_queue.put(None)