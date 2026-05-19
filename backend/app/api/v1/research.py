"""
app/api/v1/research.py

Research API endpoints.

Routes:
  POST   /research         — Submit a query; body IS the SSE stream
  GET    /research         — List saved reports (paginated, filterable)
  GET    /research/{id}    — Full report with structured data
  GET    /research/{id}/status — Polling fallback for non-SSE clients
  PATCH  /research/{id}    — Update title, tags, is_pinned
  DELETE /research/{id}    — Archive (soft delete)

SSE streaming design:
  The POST endpoint returns Content-Type: text/event-stream.
  Events are pushed by the ReportStateMachine through the SSE queue.
  A keepalive comment line is emitted every 15 s to prevent proxy timeouts.
  The generator exits when it receives the sentinel (None) or on client disconnect.
"""
from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_analyst
from app.db.session import get_db
from app.models.domain.tenant import TenantContext
from app.models.schemas.requests.research import ReportUpdateRequest, ResearchQueryRequest
from app.models.schemas.responses.research import (
    ReportListResponse,
    ResearchReportResponse,
)
from app.orchestration.state_machine import SSEEvent
from app.services.research_service import RateLimitExceeded, ResearchService

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/research", tags=["Research"])

# ── SSE generator ──────────────────────────────────────────────────────────────

async def _sse_generator(queue: asyncio.Queue) -> AsyncIterator[bytes]:
    """
    Drain the SSE queue until the sentinel is received or the client disconnects.

    Protocol:
      - Normal event  → yield SSEEvent.to_sse_bytes()
      - None sentinel → break (engine finished)
      - 15 s timeout  → yield SSE comment keepalive (prevents proxy timeout)
      - GeneratorExit → client disconnected; log and exit cleanly
    """
    try:
        while True:
            try:
                event: SSEEvent | None = await asyncio.wait_for(
                    queue.get(), timeout=15.0
                )
            except asyncio.TimeoutError:
                # SSE comment lines keep the connection alive without
                # appearing as a named event on the client side
                yield b": keepalive\n\n"
                continue

            if event is None:
                # Sentinel — engine has completed or failed
                break

            yield event.to_sse_bytes()

    except GeneratorExit:
        log.info("sse.client_disconnected")


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post(
    "",
    summary="Submit research query (SSE stream)",
    description=(
        "Accepts a natural language research query and returns a Server-Sent Events "
        "stream. Events track each lifecycle phase (planning → dispatching → "
        "synthesizing → completed) and include the full ResearchReport JSON in the "
        "final `report.completed` or `report.partial` event.\n\n"
        "Use `GET /research/{id}/status` for polling-based clients."
    ),
    response_class=StreamingResponse,
    status_code=status.HTTP_200_OK,
)
async def submit_research_query(
    body: ResearchQueryRequest,
    ctx: TenantContext = Depends(require_analyst),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    service = ResearchService(session)

    try:
        report_id, sse_queue = await service.submit_query(body, ctx)
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": str(exc),
                "retry_after_seconds": 3600,
            },
            headers={"Retry-After": "3600"},
        ) from exc

    log.info(
        "research.sse_stream_opened",
        report_id=str(report_id),
        user_id=str(ctx.user_id),
    )

    return StreamingResponse(
        _sse_generator(sse_queue),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",       # Disables nginx buffering
            "Connection": "keep-alive",
            "X-Report-Id": str(report_id),   # Lets clients correlate without parsing events
        },
    )


@router.get(
    "",
    response_model=ReportListResponse,
    summary="List saved reports",
)
async def list_reports(
    ctx: TenantContext = Depends(require_analyst),
    session: AsyncSession = Depends(get_db),
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Results per page")] = 20,
    report_status: Annotated[
        str | None, Query(alias="status", description="Filter by status")
    ] = None,
    company: Annotated[
        str | None, Query(description="Filter by ticker symbol e.g. NVDA")
    ] = None,
    pinned: Annotated[bool, Query(description="Return only pinned reports")] = False,
) -> ReportListResponse:
    companies_filter = [company.upper()] if company else None
    return await ResearchService(session).list_reports(
        ctx=ctx,
        page=page,
        page_size=page_size,
        status_filter=report_status,
        companies_filter=companies_filter,
        pinned_only=pinned,
    )


@router.get(
    "/{report_id}",
    response_model=ResearchReportResponse,
    summary="Get a single report with full structured data",
)
async def get_report(
    report_id: uuid.UUID,
    ctx: TenantContext = Depends(require_analyst),
    session: AsyncSession = Depends(get_db),
) -> ResearchReportResponse:
    return await ResearchService(session).get_report(report_id, ctx)


@router.get(
    "/{report_id}/status",
    summary="Poll report status (non-SSE fallback)",
    description=(
        "Returns the current lifecycle status of a report without streaming. "
        "Use this endpoint when the client cannot maintain an SSE connection. "
        "Poll at 2–5 second intervals until status is completed, partial, or failed."
    ),
)
async def get_report_status(
    report_id: uuid.UUID,
    ctx: TenantContext = Depends(require_analyst),
    session: AsyncSession = Depends(get_db),
) -> dict:
    report = await ResearchService(session).get_report(report_id, ctx)
    return {
        "report_id": report.id,
        "status": report.status,
        "processing_time_ms": report.processing_time_ms,
        "created_at": report.created_at,
        "error_message": report.error_message,
        "companies": report.companies,
    }


@router.patch(
    "/{report_id}",
    response_model=ResearchReportResponse,
    summary="Update report metadata",
    description="Update title, tags, or pinned state. All fields are optional.",
)
async def update_report(
    report_id: uuid.UUID,
    body: ReportUpdateRequest,
    ctx: TenantContext = Depends(require_analyst),
    session: AsyncSession = Depends(get_db),
) -> ResearchReportResponse:
    return await ResearchService(session).update_report(report_id, body, ctx)


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Archive a report",
    description="Soft-deletes the report (is_archived=True). The data is retained in the database.",
)
async def archive_report(
    report_id: uuid.UUID,
    ctx: TenantContext = Depends(require_analyst),
    session: AsyncSession = Depends(get_db),
) -> None:
    await ResearchService(session).archive_report(report_id, ctx)
