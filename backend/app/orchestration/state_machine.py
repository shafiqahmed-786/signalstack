"""
app/orchestration/state_machine.py

Report lifecycle state machine.

Every state transition:
  1. Validates the transition is legal (raises InvalidTransitionError otherwise)
  2. Persists the new status to the database
  3. Emits a structured log entry
  4. Puts an SSEEvent onto the asyncio queue for streaming to the client

The state machine is the authoritative source of truth for the report's lifecycle.
The frontend mirrors this state machine to drive the streaming UX.

Valid transitions:
  CREATED → PLANNING | FAILED
  PLANNING → DISPATCHING | FAILED
  DISPATCHING → SYNTHESIZING | FAILED
  SYNTHESIZING → COMPLETED | PARTIAL | FAILED
  COMPLETED, PARTIAL, FAILED, CANCELLED → (terminal — no further transitions)

SSE event sequence for a successful run:
  report.planning
  report.dispatching  (includes the ResearchPlan: companies + tools)
  tool.started        (one per tool)
  tool.completed      (one per tool that succeeded)
  tool.failed         (one per tool that failed)
  report.synthesizing
  report.completed    (includes the full ResearchReport JSON)
"""
from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog

from app.models.domain.research import ReportStatus

log = structlog.get_logger(__name__)

# ── Valid transitions ──────────────────────────────────────────────────────────

VALID_TRANSITIONS: dict[ReportStatus, frozenset[ReportStatus]] = {
    ReportStatus.CREATED: frozenset({ReportStatus.PLANNING, ReportStatus.FAILED}),
    ReportStatus.PLANNING: frozenset({ReportStatus.DISPATCHING, ReportStatus.FAILED}),
    ReportStatus.DISPATCHING: frozenset({ReportStatus.SYNTHESIZING, ReportStatus.FAILED}),
    ReportStatus.SYNTHESIZING: frozenset({
        ReportStatus.COMPLETED,
        ReportStatus.PARTIAL,
        ReportStatus.FAILED,
    }),
    ReportStatus.COMPLETED: frozenset(),
    ReportStatus.PARTIAL: frozenset(),
    ReportStatus.FAILED: frozenset(),
    ReportStatus.CANCELLED: frozenset(),
}


# ── SSE event types ────────────────────────────────────────────────────────────

@dataclass
class SSEEvent:
    """
    A single Server-Sent Event.

    event   — the event type string (e.g., "report.planning", "tool.completed")
    data    — JSON-serialisable payload dict

    The client receives:
      event: report.planning\n
      data: {"status": "planning"}\n\n
    """
    event: str
    data: dict[str, Any]

    def to_sse_bytes(self) -> bytes:
        """Serialise to the SSE wire format."""
        data_str = json.dumps(self.data, default=str)
        return f"event: {self.event}\ndata: {data_str}\n\n".encode("utf-8")


# ── Exceptions ────────────────────────────────────────────────────────────────

class InvalidTransitionError(Exception):
    """
    Raised when a state transition is attempted that violates the state machine.

    This is a programming error, not a user error — it should never reach
    the client. If it does, the orchestration engine has a bug.
    """

    def __init__(
        self, from_status: ReportStatus, to_status: ReportStatus
    ) -> None:
        super().__init__(
            f"Invalid state transition: {from_status.value} → {to_status.value}. "
            f"Allowed transitions from {from_status.value}: "
            f"{[s.value for s in VALID_TRANSITIONS[from_status]]}"
        )
        self.from_status = from_status
        self.to_status = to_status


# ── State machine ──────────────────────────────────────────────────────────────

class ReportStateMachine:
    """
    Governs the report lifecycle for a single orchestration run.

    Instantiated by the OrchestrationEngine for each research query.
    The SSE queue is read by the streaming HTTP endpoint and forwarded
    to the connected client.

    Parameters
    ----------
    report_id   : UUID of the research_reports row
    sse_queue   : asyncio.Queue that the SSE endpoint drains
    report_repo : ReportRepository for DB persistence (injected to avoid
                  circular imports between engine and repository)
    """

    def __init__(
        self,
        report_id: uuid.UUID,
        sse_queue: asyncio.Queue,
        report_repo: Any,  # ReportRepository — typed as Any to avoid circular import
    ) -> None:
        self.report_id = report_id
        self._sse_queue = sse_queue
        self._repo = report_repo
        self._current = ReportStatus.CREATED

    @property
    def current_status(self) -> ReportStatus:
        return self._current

    @property
    def is_terminal(self) -> bool:
        return self._current.is_terminal

    async def transition(
        self,
        to_status: ReportStatus,
        metadata: dict[str, Any] | None = None,
        report_data: dict | None = None,
        error_message: str | None = None,
    ) -> None:
        """
        Execute a state transition.

        Parameters
        ----------
        to_status     : Target state
        metadata      : Extra data emitted in the SSE event payload
        report_data   : Full ResearchReport JSON dict (only set on COMPLETED/PARTIAL)
        error_message : Human-readable error (only set on FAILED)

        Raises
        ------
        InvalidTransitionError : If the transition violates the state machine
        """
        allowed = VALID_TRANSITIONS[self._current]
        if to_status not in allowed:
            raise InvalidTransitionError(self._current, to_status)

        from_status = self._current
        self._current = to_status

        log.info(
            "report.state_transition",
            report_id=str(self.report_id),
            from_status=from_status.value,
            to_status=to_status.value,
            metadata=metadata or {},
        )

        # 1. Persist to DB
        await self._repo.update_status(
            report_id=self.report_id,
            status=to_status,
            report_data=report_data,
            error_message=error_message,
        )

        # 2. Emit SSE event
        event_payload: dict[str, Any] = {
            "report_id": str(self.report_id),
            "status": to_status.value,
        }
        if metadata:
            event_payload.update(metadata)
        if report_data and to_status in (ReportStatus.COMPLETED, ReportStatus.PARTIAL):
            event_payload["report"] = report_data
        if error_message:
            event_payload["error"] = error_message

        event_name = f"report.{to_status.value}"
        await self._emit(SSEEvent(event=event_name, data=event_payload))

    async def emit_tool_started(self, tool: str, tickers: list[str]) -> None:
        """Emit a tool.started SSE event without changing report status."""
        await self._emit(SSEEvent(
            event="tool.started",
            data={
                "report_id": str(self.report_id),
                "tool": tool,
                "tickers": tickers,
            },
        ))

    async def emit_tool_completed(
        self,
        tool: str,
        confidence: str,
        duration_ms: int,
    ) -> None:
        """Emit a tool.completed SSE event."""
        await self._emit(SSEEvent(
            event="tool.completed",
            data={
                "report_id": str(self.report_id),
                "tool": tool,
                "confidence": confidence,
                "duration_ms": duration_ms,
            },
        ))

    async def emit_tool_failed(
        self,
        tool: str,
        error: str,
    ) -> None:
        """Emit a tool.failed SSE event."""
        await self._emit(SSEEvent(
            event="tool.failed",
            data={
                "report_id": str(self.report_id),
                "tool": tool,
                "error": error,
                "will_retry": False,
            },
        ))

    async def emit_sentinel(self) -> None:
        """
        Push a sentinel None value onto the SSE queue to signal stream end.
        The SSE endpoint loop breaks when it receives None.
        """
        await self._sse_queue.put(None)

    async def _emit(self, event: SSEEvent) -> None:
        """Put an event onto the SSE queue. Never raises — queue errors are logged."""
        try:
            await self._sse_queue.put(event)
        except Exception as exc:
            log.error(
                "state_machine.sse_queue_error",
                report_id=str(self.report_id),
                event=event.event,
                error=str(exc),
            )