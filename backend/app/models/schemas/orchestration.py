"""
Orchestration Schemas — SSE Events, Config Display, Progress Tracking
======================================================================
Defines the wire formats for:

  1. SSE event payloads (streamed to the frontend during orchestration)
  2. Public representation of OrchestratorConfig (for health/debug endpoints)
  3. Plan preview (returned immediately when the planner completes)

SSE Event Format (text/event-stream):
  event: {SSEEventType value}
  data: {JSON-serialized SSE event payload}
  id: {monotonic integer for reconnection}

Frontend consumes these events to:
  - Show tool progress badges (tool_started → tool_completed/tool_failed)
  - Update status banners (state_changed)
  - Render the full report (report_completed)
  - Show error state with retry button (report_failed)
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


# ── SSE Event Types ────────────────────────────────────────────────────────────

class SSEEventType(str, Enum):
    """All possible SSE events emitted during a research orchestration run."""

    CONNECTED = "connected"             # Initial connection handshake
    PLAN_READY = "plan_ready"           # Planner completed, tools are known
    TOOL_STARTED = "tool_started"       # Individual tool execution began
    TOOL_COMPLETED = "tool_completed"   # Individual tool succeeded
    TOOL_FAILED = "tool_failed"         # Individual tool failed (non-fatal)
    STATE_CHANGED = "state_changed"     # Report status machine transition
    SYNTHESIS_STARTED = "synthesis_started"  # OpenAI synthesis call began
    REPORT_COMPLETED = "report_completed"    # Full ResearchReport ready
    REPORT_PARTIAL = "report_partial"        # Partial success — report ready with gaps
    REPORT_FAILED = "report_failed"          # Fatal failure — no report produced
    HEARTBEAT = "heartbeat"             # Keep-alive ping every 15s


# ── SSE Event Payload Models ───────────────────────────────────────────────────

class ConnectedEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: str
    message: str = "Connected to research stream"


class PlanReadyEvent(BaseModel):
    """
    Emitted immediately when the planner returns.
    Frontend renders tool badges in "pending" state for each tool.
    """

    model_config = ConfigDict(frozen=True)

    report_id: str
    companies: list[str]
    query_intent: str
    tools_to_execute: list[str]          # Tool names in planned execution order
    requires_comparison: bool


class ToolStartedEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: str
    tool: str
    tickers: list[str]


class ToolCompletedEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: str
    tool: str
    confidence_level: str               # "high" | "medium" | "low"
    items_returned: int | None = None   # Articles, chunks, companies, etc.
    duration_ms: float | None = None


class ToolFailedEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: str
    tool: str
    error_type: str                     # "timeout" | "api_error" | "validation_error"
    message: str
    fatal: bool = False                 # True only if this failure aborts the whole run


class StateChangedEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: str
    from_status: str
    to_status: str
    message: str | None = None


class SynthesisStartedEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: str
    tools_succeeded: list[str]
    tools_failed: list[str]
    message: str = "Generating structured research report..."


class ReportCompletedEvent(BaseModel):
    """
    Terminal success event. 'report' is the full ResearchReport JSON.
    Frontend renders the full report upon receiving this event.
    """

    model_config = ConfigDict(frozen=True)

    report_id: str
    status: str                          # "completed" | "partial_success"
    processing_time_ms: int | None = None
    total_tokens_used: int | None = None
    # The full report is included in this event so the client doesn't need
    # to make a separate GET request after the stream closes.
    report: dict                         # ResearchReport.model_dump(mode='json')


class ReportFailedEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: str
    error_code: str                      # "PLANNER_FAILED" | "ALL_TOOLS_FAILED" | "SYNTHESIS_FAILED"
    message: str
    retry_allowed: bool = True


class HeartbeatEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_id: str
    current_status: str


# ── SSE Envelope ───────────────────────────────────────────────────────────────

class SSEEnvelope(BaseModel):
    """
    Wire format for a single SSE message.
    Serialized as:
      event: {event_type}
      data: {json_payload}
      id: {sequence_id}

    Note: 'data' must be a single-line JSON string in SSE format.
    The SSE endpoint serializes payload using model_dump_json().
    """

    model_config = ConfigDict(frozen=True)

    event: SSEEventType
    payload: dict                        # model_dump() of the specific event model
    sequence_id: int                     # Monotonic counter for SSE reconnection

    def to_sse_string(self) -> str:
        """Format as a valid SSE message string."""
        import json
        payload_str = json.dumps(self.payload, separators=(",", ":"))
        return (
            f"event: {self.event.value}\n"
            f"data: {payload_str}\n"
            f"id: {self.sequence_id}\n\n"
        )


# ── Config Display Schema ──────────────────────────────────────────────────────

class OrchestratorConfigResponse(BaseModel):
    """
    Public representation of OrchestratorConfig.
    Returned by a debug/admin endpoint to show current orchestration settings.
    Does NOT expose API keys or credentials.
    """

    model_config = ConfigDict(frozen=True)

    planner_model: str
    synthesizer_model: str
    sentiment_model: str
    embedding_model: str

    max_companies_per_query: int
    max_tools_per_plan: int
    max_news_articles_to_synthesizer: int
    max_vector_chunks_to_synthesizer: int
    max_historical_price_points: int

    tool_timeouts: dict[str, float]
    orchestration_total_timeout: float

    llm_max_retries: int
    tool_max_retries: int

    embedding_relevance_threshold: float

    cache_ttl_market_data_seconds: int
    cache_ttl_news_seconds: int
    cache_ttl_filings_seconds: int

    token_budgets: dict[str, int]


# ── Plan Preview ───────────────────────────────────────────────────────────────

class PlanPreviewResponse(BaseModel):
    """
    Immediate response body when POST /research is called in synchronous mode.
    Gives the client a preview of what the system will do before it does it.
    Used for the "plan confirmation" UX pattern (optional — can be skipped).
    """

    model_config = ConfigDict(frozen=True)

    report_id: str
    companies: list[str]
    query_intent: str
    tools_to_execute: list[str]
    requires_comparison: bool
    requires_historical_prices: bool
    requires_filing_context: bool
    planner_reasoning: str
    estimated_duration_seconds: float = Field(
        description="Rough estimate based on tools to execute and typical latencies"
    )