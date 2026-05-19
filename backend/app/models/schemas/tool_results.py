"""
Tool Result Schemas — Observability and Logging DTOs
======================================================
These schemas define the serializable representation of tool results
for three purposes:

  1. Structured logging: logged as JSON at each tool completion
  2. GenerationContext storage: a compact summary stored alongside report_data
  3. Debug/admin API responses (future): could expose orchestration details

These are intentionally leaner than the domain tool result models —
they strip internal state and format for external consumption.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ── Per-tool execution log entries ─────────────────────────────────────────────

class MarketDataLogEntry(BaseModel):
    """Logged when MarketDataTool completes (success or failure)."""

    model_config = ConfigDict(frozen=True)

    tool: str = "market_data"
    tickers_requested: list[str]
    tickers_succeeded: list[str]
    tickers_failed: list[str]
    data_source: str                     # "yahoo_finance" | "alpha_vantage" | "mock"
    is_delayed: bool
    confidence_level: str
    duration_ms: float | None = None
    error_message: str | None = None


class NewsSearchLogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool: str = "news_search"
    tickers_requested: list[str]
    articles_fetched: int
    articles_per_ticker: dict[str, int]
    data_source: str
    confidence_level: str
    duration_ms: float | None = None
    error_message: str | None = None


class SentimentLogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool: str = "sentiment_analysis"
    articles_analyzed: int
    companies_covered: list[str]
    input_tokens: int
    output_tokens: int
    confidence_level: str
    duration_ms: float | None = None
    error_message: str | None = None


class SECFilingLogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool: str = "sec_filings"
    tickers_queried: list[str]
    semantic_query: str
    chunks_retrieved: int
    avg_relevance_score: float | None = None
    top_relevance_score: float | None = None
    confidence_level: str
    duration_ms: float | None = None
    error_message: str | None = None


class ToolFailureLogEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    tool: str
    tickers: list[str]
    error_type: str
    error_message: str
    retried: bool
    retry_count: int
    duration_ms: float | None = None


# ── Complete orchestration run log ─────────────────────────────────────────────

class OrchestrationRunLog(BaseModel):
    """
    Single structured JSON log entry emitted at the end of each orchestration run.
    Captured by structlog and emitted to stdout → log aggregator.

    This is the single authoritative record of what happened in one research query.
    """

    model_config = ConfigDict(frozen=True)

    # Correlation IDs
    report_id: str
    request_id: str | None
    org_id: str
    user_id: str

    # Input
    query_length: int
    companies_queried: list[str]
    query_intent: str
    tools_planned: list[str]

    # Execution
    tools_succeeded: list[str]
    tools_failed: list[str]
    partial_failure: bool
    cache_hit: bool

    # Tool details
    market_data: MarketDataLogEntry | None = None
    news_search: NewsSearchLogEntry | None = None
    sentiment: SentimentLogEntry | None = None
    sec_filings: SECFilingLogEntry | None = None
    failures: list[ToolFailureLogEntry] = Field(default_factory=list)

    # Token accounting
    planner_tokens_in: int
    planner_tokens_out: int
    synthesizer_tokens_in: int
    synthesizer_tokens_out: int
    sentiment_tokens_in: int
    sentiment_tokens_out: int
    total_tokens: int

    # Cost estimate (USD)
    estimated_cost_usd: float

    # Timing (ms)
    plan_duration_ms: float | None
    dispatch_duration_ms: float | None
    sentiment_duration_ms: float | None
    retrieval_duration_ms: float | None
    synthesis_duration_ms: float | None
    total_duration_ms: float | None

    # Outcome
    final_status: str
    error_message: str | None


# ── Compact generation context summary ────────────────────────────────────────

class GenerationContextSummary(BaseModel):
    """
    Compact version of GenerationContext for display in list views.
    Used when we want to show basic provenance without the full nested object.
    """

    model_config = ConfigDict(frozen=True)

    planner_model: str
    synthesizer_model: str
    total_tokens: int
    tools_used: list[str]
    partial_failure: bool
    cache_hit: bool
    estimated_cost_usd: float