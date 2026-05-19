"""
app/repositories/report_repository.py

Data-access layer for research_reports.
All DB operations are scoped to a single organization (tenant).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db.report import ResearchReport
from app.models.domain.research import ReportStatus
from app.models.domain.tenant import TenantContext
from app.repositories.base import TenantAwareRepository

log = structlog.get_logger(__name__)


class ReportRepository(TenantAwareRepository):
    """CRUD + lifecycle operations for ResearchReport rows."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ── Write operations ───────────────────────────────────────────────────────

    async def create(
        self,
        *,
        query: str,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        companies: list[str] | None = None,
    ) -> ResearchReport:
        report = ResearchReport(
            id=uuid.uuid4(),
            query=query,
            organization_id=org_id,
            created_by=user_id,
            companies=companies or [],
            status=ReportStatus.CREATED.value,
        )
        self._session.add(report)
        await self._session.flush()
        await self._session.refresh(report)
        log.info("report.created", report_id=str(report.id), org_id=str(org_id))
        return report

    async def update_status(
        self,
        *,
        report_id: uuid.UUID,
        status: ReportStatus,
        report_data: dict | None = None,
        error_message: str | None = None,
        processing_time_ms: int | None = None,
        total_tokens_used: int | None = None,
        model_used: str | None = None,
        tools_called: list[str] | None = None,
        companies: list[str] | None = None,
    ) -> None:
        values: dict[str, Any] = {"status": status.value}
        if report_data is not None:
            values["report_data"] = report_data
        if error_message is not None:
            values["error_message"] = error_message
        if processing_time_ms is not None:
            values["processing_time_ms"] = processing_time_ms
        if total_tokens_used is not None:
            values["total_tokens_used"] = total_tokens_used
        if model_used is not None:
            values["model_used"] = model_used
        if tools_called is not None:
            values["tools_called"] = tools_called
        if companies is not None:
            values["companies"] = companies

        stmt = (
            update(ResearchReport)
            .where(ResearchReport.id == report_id)
            .values(**values)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def update_metadata(
        self,
        *,
        report_id: uuid.UUID,
        ctx: TenantContext,
        title: str | None = None,
        tags: list[str] | None = None,
        is_pinned: bool | None = None,
    ) -> ResearchReport:
        org_id = self._require_tenant(ctx)
        stmt = select(ResearchReport).where(
            ResearchReport.id == report_id,
            self._org_filter(ResearchReport, ctx),
        )
        result = await self._session.execute(stmt)
        report = result.scalar_one_or_none()
        if report is None:
            from fastapi import HTTPException, status as http_status
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail={"code": "REPORT_NOT_FOUND", "report_id": str(report_id)},
            )
        if title is not None:
            report.title = title
        if tags is not None:
            report.tags = tags
        if is_pinned is not None:
            report.is_pinned = is_pinned
        await self._session.flush()
        await self._session.refresh(report)
        return report

    async def archive(
        self,
        *,
        report_id: uuid.UUID,
        ctx: TenantContext,
    ) -> None:
        stmt = (
            update(ResearchReport)
            .where(
                ResearchReport.id == report_id,
                self._org_filter(ResearchReport, ctx),
            )
            .values(is_archived=True)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    # ── Read operations ────────────────────────────────────────────────────────

    async def get_by_id(
        self,
        report_id: uuid.UUID,
        ctx: TenantContext,
    ) -> ResearchReport:
        stmt = select(ResearchReport).where(
            ResearchReport.id == report_id,
            self._org_filter(ResearchReport, ctx),
        )
        result = await self._session.execute(stmt)
        report = result.scalar_one_or_none()
        if report is None:
            from fastapi import HTTPException, status as http_status
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail={"code": "REPORT_NOT_FOUND", "report_id": str(report_id)},
            )
        return report

    async def list_reports(
        self,
        *,
        ctx: TenantContext,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
        companies_filter: list[str] | None = None,
        pinned_only: bool = False,
    ) -> tuple[list[ResearchReport], int]:
        org_id = self._require_tenant(ctx)
        base = select(ResearchReport).where(
            self._org_filter(ResearchReport, ctx),
            ResearchReport.is_archived.is_(False),
        )
        if status_filter:
            base = base.where(ResearchReport.status == status_filter)
        if companies_filter:
            for ticker in companies_filter:
                base = base.where(ResearchReport.companies.any(ticker))
        if pinned_only:
            base = base.where(ResearchReport.is_pinned.is_(True))

        count_stmt = select(func.count()).select_from(base.subquery())
        total_result = await self._session.execute(count_stmt)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        data_stmt = (
            base.order_by(ResearchReport.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        data_result = await self._session.execute(data_stmt)
        rows = list(data_result.scalars().all())
        return rows, total

    async def count_today(
        self,
        *,
        org_id: uuid.UUID,
    ) -> int:
        today = datetime.now(timezone.utc).date()
        stmt = select(func.count()).where(
            ResearchReport.organization_id == org_id,
            func.date(ResearchReport.created_at) == today,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def count_this_hour(
        self,
        *,
        org_id: uuid.UUID,
    ) -> int:
        now = datetime.now(timezone.utc)
        hour_start = now.replace(minute=0, second=0, microsecond=0)
        stmt = select(func.count()).where(
            ResearchReport.organization_id == org_id,
            ResearchReport.created_at >= hour_start,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
