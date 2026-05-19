"""
Orchestration Domain Models
============================
Contains the full type system for the AI orchestration pipeline:
  - Report lifecycle state machine (11 states + valid transitions)
  - Planner output models (OpenAI-facing and validated domain versions)
  - Orchestrator runtime config (derived from Settings, injected everywhere)
  - Orchestration metrics for observability
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from app.config import Settings


# ── State Machine ──────────────────────────────────────────────────────────────

class ReportStatus(str, Enum):
    """
    11-state lifecycle for a research report.

    Terminal states: COMPLETED, PARTIAL_SUCCESS, FAILED

    PARTIAL_SUCCESS: At least one tool failed but synthesis succeeded
                     with remaining data. The report exists but has data_gaps.
    """

    QUEUED = "queued"
    PLANNING = "planning"
    FETCHING_DATA = "fetching_data"
    RUNNING_SENTIMENT = "running_sentiment"
    RETRIEVING_CONTEXT = "retrieving_context"
    SYNTHESIZING = "synthesizing"
    VALIDATING = "validating"
    SAVING = "saving"
    COMPLETED = "completed"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in {
            ReportStatus.COMPLETED,
            ReportStatus.PARTIAL_SUCCESS,
            ReportStatus.FAILED,
        }

    @property
    def is_active(self) -> bool:
        return not self.is_terminal


VALID_TRANSITIONS: dict[ReportStatus, frozenset[ReportStatus]] = {
    ReportStatus.QUEUED: frozenset({
        ReportStatus.PLANNING,
        ReportStatus.FAILED,
    }),
    ReportStatus.PLANNING: frozenset({
        ReportStatus.FETCHING_DATA,
        ReportStatus.FAILED,
    }),
    ReportStatus.FETCHING_DATA: frozenset({
        # Can skip RUNNING_SENTIMENT if query doesn't need it
        ReportStatus.RUNNING_SENTIMENT,
        ReportStatus.RETRIEVING_CONTEXT,
        ReportStatus.SYNTHESIZING,     # Skip retrieval if no vector data needed
        ReportStatus.FAILED,
    }),
    ReportStatus.RUNNING_SENTIMENT: frozenset({
        ReportStatus.RETRIEVING_CONTEXT,
        ReportStatus.SYNTHESIZING,
        ReportStatus.FAILED,
    }),
    ReportStatus.RETRIEVING_CONTEXT: frozenset({
        ReportStatus.SYNTHESIZING,
        ReportStatus.FAILED,
    }),
    ReportStatus.SYNTHESIZING: frozenset({
        ReportStatus.VALIDATING,
        ReportStatus.FAILED,
    }),
    ReportStatus.VALIDATING: frozenset({
        ReportStatus.SAVING,
        ReportStatus.FAILED,
    }),
    ReportStatus.SAVING: frozenset({
        ReportStatus.COMPLETED,
        ReportStatus.PARTIAL_SUCCESS,
        ReportStatus.FAILED,
    }),
    # Terminal states: no valid transitions out
    ReportStatus.COMPLETED: frozenset(),
    ReportStatus.PARTIAL_SUCCESS: frozenset(),
    ReportStatus.FAILED: frozenset(),
}


class StateTransition(BaseModel):
    """Record of a single state machine transition — logged and streamed via SSE."""

    model_config = ConfigDict(frozen=True)

    report_id: str
    from_status: ReportStatus
    to_status: ReportStatus
    transitioned_at: str = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )
    metadata: dict[str, object] = Field(default_factory=dict)
    error_message: str | None = None


# ── Query Intent ───────────────────────────────────────────────────────────────

class QueryIntent(str, Enum):
    """
    Semantic intent of the research query.
    The Planner classifies the query into one of these intent categories,
    which influences which sections the Synthesizer should generate.
    """

    COMPANY_OVERVIEW = "company_overview"
    EARNINGS_ANALYSIS = "earnings_analysis"
    NEWS_SUMMARY = "news_summary"
    COMPETITOR_COMPARISON = "competitor_comparison"
    RISK_ASSESSMENT = "risk_assessment"
    FINANCIAL_METRICS = "financial_metrics"
    FILING_ANALYSIS = "filing_analysis"
    GENERAL_RESEARCH = "general_research"


# ── OpenAI-Compatible Planner Output ──────────────────────────────────────────

class PlannerToolCall(BaseModel):
    """
    A single tool invocation as planned by the Planner.
    Uses str for tool names (not ToolName enum) for OpenAI schema compatibility.
    Validated against the tool registry after OpenAI returns the output.
    """

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"additionalProperties": False},
    )

    tool: str
    # Ticker symbols for this specific tool call (may be subset of all companies)
    tickers: list[str]
    # Semantic query for vector retrieval and SEC filings tools — null for others
    semantic_query: str | None = None
    reasoning: str


class PlannerOutput(BaseModel):
    """
    Direct structured output from OpenAI for the Planner.

    Passed to: client.beta.chat.completions.parse(response_format=PlannerOutput)

    The Planner is called once per research request with:
      - The user's raw query
      - Available tool descriptions
      - Company name → ticker resolution hints
      - Today's date for temporal context
    """

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"additionalProperties": False},
    )

    # Ticker symbols identified in the query (uppercase, e.g. ["NVDA", "AMD"])
    companies: list[str]
    # Semantic intent — must match QueryIntent enum value
    query_intent: str
    # Ordered list of tool calls to execute
    tools_needed: list[PlannerToolCall]
    # Whether the query requires side-by-side comparison of multiple companies
    requires_comparison: bool
    # Whether historical price data is needed (for trend analysis)
    requires_historical_prices: bool
    # Whether SEC filing / earnings transcript data is needed
    requires_filing_context: bool
    # Planner's reasoning — logged for observability, not shown to the user
    reasoning: str


# ── Validated Domain Plan ──────────────────────────────────────────────────────

class ValidatedToolCall(BaseModel):
    """
    Tool call after validation against the tool registry whitelist.
    'tool' is now a strongly-typed ToolName (imported lazily to avoid circular imports).
    """

    model_config = ConfigDict(frozen=True)

    tool: str              # Validated ToolName string value
    tickers: list[str]     # Validated uppercase ticker symbols
    semantic_query: str | None = None
    reasoning: str


class ResearchPlan(BaseModel):
    """
    Validated, domain-typed version of PlannerOutput.
    Built by the Planner service after validating PlannerOutput.

    Guarantee: all tool names are in the allowed whitelist,
    all tickers are uppercase and within the configured limit,
    query_intent is a valid QueryIntent enum value.
    """

    model_config = ConfigDict(frozen=True)

    companies: list[str]
    query_intent: QueryIntent
    tool_calls: list[ValidatedToolCall]
    requires_comparison: bool
    requires_historical_prices: bool
    requires_filing_context: bool
    reasoning: str
    created_at: str = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )

    @field_validator("companies", mode="after")
    @classmethod
    def normalize_tickers(cls, v: list[str]) -> list[str]:
        return [t.upper().strip() for t in v]

    @field_validator("query_intent", mode="before")
    @classmethod
    def validate_intent(cls, v: str) -> QueryIntent:
        try:
            return QueryIntent(v)
        except ValueError:
            return QueryIntent.GENERAL_RESEARCH


# ── Orchestrator Runtime Config ────────────────────────────────────────────────

class OrchestratorConfig(BaseModel):
    """
    Immutable runtime configuration for the orchestration layer.
    Derived from Settings at application startup via from_settings().
    Injected into all orchestration services via FastAPI Depends().

    Never instantiated with raw values — always via from_settings().
    This decouples the orchestration layer from the Settings system.
    """

    model_config = ConfigDict(frozen=True)

    # ── Model identifiers ────────────────────────────────────────
    planner_model: str
    synthesizer_model: str
    sentiment_model: str
    embedding_model: str

    # ── Token budgets ────────────────────────────────────────────
    max_tokens_planner_input: int
    max_tokens_planner_output: int
    max_tokens_synthesis_input: int
    max_tokens_synthesis_output: int
    max_tokens_sentiment_input: int
    max_tokens_sentiment_output: int

    # ── Tool limits ──────────────────────────────────────────────
    max_companies_per_query: int
    max_tools_per_plan: int
    max_news_articles_fetched: int
    max_news_articles_to_synthesizer: int
    max_vector_chunks_fetched: int
    max_vector_chunks_to_synthesizer: int
    max_historical_price_points: int

    # ── Timeouts (seconds) ───────────────────────────────────────
    tool_timeout_market_data: float
    tool_timeout_news_search: float
    tool_timeout_vector_retrieval: float
    tool_timeout_sentiment: float
    tool_timeout_sec_filings: float
    orchestration_total_timeout: float

    # ── Retrieval ────────────────────────────────────────────────
    embedding_relevance_threshold: float

    # ── Retry policy ─────────────────────────────────────────────
    llm_max_retries: int
    tool_max_retries: int

    # ── Cache TTLs (seconds) ─────────────────────────────────────
    cache_ttl_market_data: int
    cache_ttl_news: int
    cache_ttl_filings: int

    @classmethod
    def from_settings(cls, settings: "Settings") -> "OrchestratorConfig":
        return cls(
            planner_model=settings.openai_model_planner,
            synthesizer_model=settings.openai_model_synthesizer,
            sentiment_model=settings.openai_model_sentiment,
            embedding_model=settings.openai_model_embedding,
            max_tokens_planner_input=settings.max_tokens_planner_input,
            max_tokens_planner_output=settings.max_tokens_planner_output,
            max_tokens_synthesis_input=settings.max_tokens_synthesis_input,
            max_tokens_synthesis_output=settings.max_tokens_synthesis_output,
            max_tokens_sentiment_input=settings.max_tokens_sentiment_input,
            max_tokens_sentiment_output=settings.max_tokens_sentiment_output,
            max_companies_per_query=settings.max_companies_per_query,
            max_tools_per_plan=settings.max_tools_per_plan,
            max_news_articles_fetched=settings.max_news_articles_fetched,
            max_news_articles_to_synthesizer=settings.max_news_articles_to_synthesizer,
            max_vector_chunks_fetched=settings.max_vector_chunks_fetched,
            max_vector_chunks_to_synthesizer=settings.max_vector_chunks_to_synthesizer,
            max_historical_price_points=settings.max_historical_price_points,
            tool_timeout_market_data=settings.tool_timeout_market_data,
            tool_timeout_news_search=settings.tool_timeout_news_search,
            tool_timeout_vector_retrieval=settings.tool_timeout_vector_retrieval,
            tool_timeout_sentiment=settings.tool_timeout_sentiment,
            tool_timeout_sec_filings=settings.tool_timeout_sec_filings,
            orchestration_total_timeout=settings.orchestration_total_timeout,
            embedding_relevance_threshold=settings.embedding_relevance_threshold,
            llm_max_retries=settings.llm_max_retries,
            tool_max_retries=settings.tool_max_retries,
            cache_ttl_market_data=settings.cache_ttl_market_data,
            cache_ttl_news=settings.cache_ttl_news,
            cache_ttl_filings=settings.cache_ttl_filings,
        )

    def tool_timeout(self, tool_name: str) -> float:
        """Convenience accessor for per-tool timeout by string name."""
        mapping: dict[str, float] = {
            "market_data": self.tool_timeout_market_data,
            "news_search": self.tool_timeout_news_search,
            "vector_retrieval": self.tool_timeout_vector_retrieval,
            "sentiment_analysis": self.tool_timeout_sentiment,
            "sec_filings": self.tool_timeout_sec_filings,
        }
        return mapping.get(tool_name, 8.0)


# ── Observability Metrics ─────────────────────────────────────────────────────

class ToolExecutionMetric(BaseModel):
    """Per-tool timing and outcome record. One entry per tool invocation."""

    model_config = ConfigDict(frozen=True)

    tool_name: str
    tickers: list[str]
    started_at: str                         # ISO datetime string
    completed_at: str | None = None
    duration_ms: float | None = None
    status: str                             # "success" | "partial" | "failed" | "timeout"
    confidence_score: float | None = None
    error_type: str | None = None
    error_message: str | None = None
    items_returned: int | None = None       # Articles, chunks, etc.


class OrchestrationMetrics(BaseModel):
    """
    Complete observability record for a single orchestration run.
    Stored in GenerationContext and logged as a structured JSON event.
    """

    model_config = ConfigDict(frozen=True)

    report_id: str
    request_id: str | None = None
    org_id: str
    user_id: str
    query_hash: str                         # Hash of the normalized query

    # Timing
    started_at: str
    completed_at: str | None = None
    plan_duration_ms: float | None = None
    dispatch_duration_ms: float | None = None
    sentiment_duration_ms: float | None = None
    retrieval_duration_ms: float | None = None
    synthesis_duration_ms: float | None = None
    total_duration_ms: float | None = None

    # Tool outcomes
    tool_metrics: list[ToolExecutionMetric] = Field(default_factory=list)
    tools_planned: list[str] = Field(default_factory=list)
    tools_succeeded: list[str] = Field(default_factory=list)
    tools_failed: list[str] = Field(default_factory=list)
    partial_failure: bool = False

    # Token accounting
    planner_input_tokens: int = 0
    planner_output_tokens: int = 0
    synthesizer_input_tokens: int = 0
    synthesizer_output_tokens: int = 0
    sentiment_input_tokens: int = 0
    sentiment_output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return (
            self.planner_input_tokens
            + self.planner_output_tokens
            + self.synthesizer_input_tokens
            + self.synthesizer_output_tokens
            + self.sentiment_input_tokens
            + self.sentiment_output_tokens
        )

    @property
    def estimated_cost_usd(self) -> float:
        """
        Rough cost estimate based on GPT-4o pricing (May 2025).
        Input: $2.50/M tokens, Output: $10.00/M tokens.
        Used for observability logging, not billing.
        """
        input_tokens = (
            self.planner_input_tokens
            + self.synthesizer_input_tokens
            + self.sentiment_input_tokens
        )
        output_tokens = (
            self.planner_output_tokens
            + self.synthesizer_output_tokens
            + self.sentiment_output_tokens
        )
        return (input_tokens / 1_000_000 * 2.50) + (output_tokens / 1_000_000 * 10.00)