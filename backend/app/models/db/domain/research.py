"""
Research Report Domain Models
==============================
This module defines the complete type system for research reports.

Two layers exist:

  1. OpenAI-Compatible Output Models (prefix: Synthesis*)
     - Passed directly to client.beta.chat.completions.parse()
     - Flat, no discriminated unions, no complex generics
     - All optional fields default to None or []
     - additionalProperties=False enforced via ConfigDict

  2. Full Domain Models (ResearchReport and its sub-types)
     - Rich, nested, with source attribution
     - Used for DB storage (JSONB), API responses, and frontend rendering
     - Built from SynthesisOutput via post-processing in the synthesizer layer
     - Round-trip stable: model_dump(mode='json') → model_validate()
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


# ── Enums ──────────────────────────────────────────────────────────────────────

class SentimentLabel(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RiskCategory(str, Enum):
    MARKET = "market"
    COMPETITIVE = "competitive"
    REGULATORY = "regulatory"
    OPERATIONAL = "operational"
    MACRO = "macro"
    FINANCIAL = "financial"


class SourceType(str, Enum):
    MARKET_API = "market_api"
    NEWS_API = "news_api"
    VECTOR_DB = "vector_db"
    FILING = "filing"
    LLM_SYNTHESIS = "llm_synthesis"


class DataGapSeverity(str, Enum):
    WARNING = "warning"  # Partial data — report continues but section is degraded
    ERROR = "error"      # Section omitted — insufficient data


# ── Primitive sub-types ────────────────────────────────────────────────────────

class PricePoint(BaseModel):
    """Single OHLC-lite entry for chart rendering."""

    model_config = ConfigDict(frozen=True)

    date: str              # ISO date string: "2025-05-10"
    close: float
    volume: int
    change_pct: float | None = None


class CompanyMetrics(BaseModel):
    """Key financial metrics for a single company."""

    model_config = ConfigDict(frozen=True)

    current_price: float | None = None
    market_cap: float | None = None           # USD
    pe_ratio: float | None = None
    revenue_ttm: float | None = None          # Trailing twelve months, USD
    eps: float | None = None                  # Earnings per share
    change_1d_pct: float | None = None
    change_1w_pct: float | None = None
    change_1m_pct: float | None = None
    volume: int | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    dividend_yield: float | None = None
    beta: float | None = None


class NewsSentimentSummary(BaseModel):
    """Aggregated sentiment across all news articles for a company."""

    model_config = ConfigDict(frozen=True)

    overall: SentimentLabel
    score: float           # -1.0 (most negative) to 1.0 (most positive)
    article_count: int
    positive_count: int
    negative_count: int
    neutral_count: int


# ── Source Attribution Registry ────────────────────────────────────────────────

class SourceAttribution(BaseModel):
    """
    Citation registry entry. All data points in the report reference a source_id
    that maps back to an entry in ResearchReport.sources.

    The 'id' field is a UUID string (not Python UUID) for JSON round-trip
    compatibility without custom encoders.
    """

    model_config = ConfigDict(frozen=True)

    id: str                             # UUID string
    type: SourceType
    name: str                           # e.g. "Yahoo Finance", "Reuters", "NVIDIA 10-K Q3"
    url: str | None = None
    fetched_at: str                     # ISO datetime string
    ticker: str | None = None           # Which company this source covers
    metadata: dict[str, str] = Field(default_factory=dict)


# ── Data Gap (transparency about failures) ────────────────────────────────────

class DataGap(BaseModel):
    """
    Records what the system could not retrieve during orchestration.
    Rendered as a warning banner in the UI so users know what's missing.
    """

    model_config = ConfigDict(frozen=True)

    section_type: str
    ticker: str | None = None
    reason: str
    severity: DataGapSeverity
    tool_name: str | None = None        # Which tool failed


# ── Company Snapshot ──────────────────────────────────────────────────────────

class CompanySnapshot(BaseModel):
    """
    Top-level company data card. Rendered in the UI as a company overview widget.
    price_history provides 30 days of close prices for the sparkline chart.
    source_ids reference the SourceAttribution registry for inline citations.
    """

    model_config = ConfigDict(frozen=True)

    ticker: str
    name: str
    exchange: str | None = None
    sector: str | None = None
    description: str | None = None
    metrics: CompanyMetrics
    price_history: list[PricePoint] = Field(default_factory=list)
    news_sentiment: NewsSentimentSummary | None = None
    source_ids: list[str] = Field(default_factory=list)


# ── Report Section Sub-models ──────────────────────────────────────────────────

class ComparisonMetricValue(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    value: float | None
    formatted: str           # Pre-formatted for display: "$22.1B", "68.2x", "+12.3%"


class ComparisonMetric(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str                            # "Revenue (TTM)", "P/E Ratio", "Market Cap"
    unit: str                            # "USD", "ratio", "percent"
    values: list[ComparisonMetricValue]
    winner_ticker: str | None = None     # Best performer for this metric
    insight: str                         # One-sentence AI observation
    source_ids: list[str] = Field(default_factory=list)


class EarningsHighlight(BaseModel):
    model_config = ConfigDict(frozen=True)

    period: str                          # "Q3 FY2024", "FY2024"
    revenue: float | None = None
    revenue_growth_yoy_pct: float | None = None
    eps_actual: float | None = None
    eps_estimate: float | None = None
    beat_miss: str | None = None         # "beat" | "miss" | "in_line"
    guidance: str | None = None          # Forward guidance narrative


class FilingExcerpt(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    document_title: str
    relevance_score: float
    chunk_index: int | None = None
    source_id: str                       # References SourceAttribution.id


class RiskFactor(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: RiskCategory
    title: str
    description: str
    severity: RiskLevel
    source_id: str | None = None         # Which source surfaced this risk


class NewsItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    ticker: str
    title: str
    summary: str                          # AI-compressed to 2 sentences max
    sentiment: SentimentLabel
    sentiment_score: float                # -1.0 to 1.0
    published_at: str                     # ISO datetime string
    source_name: str
    url: str
    source_id: str                        # References SourceAttribution.id


# ── Report Sections ────────────────────────────────────────────────────────────

class OverviewSection(BaseModel):
    type: Literal["overview"] = "overview"
    title: str = "Company Overview"
    narrative: str
    key_highlights: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class ComparisonSection(BaseModel):
    type: Literal["comparison"] = "comparison"
    title: str = "Comparative Analysis"
    tickers: list[str]
    metrics: list[ComparisonMetric] = Field(default_factory=list)
    commentary: str
    source_ids: list[str] = Field(default_factory=list)


class EarningsSection(BaseModel):
    type: Literal["earnings"] = "earnings"
    title: str
    ticker: str
    highlights: EarningsHighlight | None = None
    narrative: str
    filing_excerpts: list[FilingExcerpt] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class NewsSection(BaseModel):
    type: Literal["news"] = "news"
    title: str = "Recent News"
    articles: list[NewsItem] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class FilingInsightsSection(BaseModel):
    type: Literal["filing_insights"] = "filing_insights"
    title: str = "Filing Insights"
    query_used: str
    excerpts: list[FilingExcerpt] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class RiskSection(BaseModel):
    type: Literal["risk"] = "risk"
    title: str = "Risk Assessment"
    overall_level: RiskLevel
    factors: list[RiskFactor] = Field(default_factory=list)
    summary: str
    source_ids: list[str] = Field(default_factory=list)


# ── Generation Provenance ──────────────────────────────────────────────────────

class GenerationContext(BaseModel):
    """
    Immutable provenance record for reproducibility and auditability.
    Stored alongside report_data in the DB so any report can be replayed.
    """

    model_config = ConfigDict(frozen=True)

    schema_version: str = "1.0"
    planner_prompt_version: str         # e.g. "planner:1.0.0"
    synthesizer_prompt_version: str     # e.g. "synthesizer:1.0.0"
    sentiment_prompt_version: str       # e.g. "sentiment:1.0.0"
    planner_model: str
    synthesizer_model: str
    sentiment_model: str
    temperature_synthesizer: float = 0.0
    temperature_planner: float = 0.1
    # Token accounting
    planner_input_tokens: int = 0
    planner_output_tokens: int = 0
    synthesizer_input_tokens: int = 0
    synthesizer_output_tokens: int = 0
    sentiment_input_tokens: int = 0
    sentiment_output_tokens: int = 0
    total_tokens: int = 0
    # Tool execution summary
    tools_planned: list[str] = Field(default_factory=list)
    tools_succeeded: list[str] = Field(default_factory=list)
    tools_failed: list[str] = Field(default_factory=list)
    # Raw tool results hash — used for report reproducibility verification
    tool_results_hash: str | None = None
    cache_hit: bool = False


# ── Full ResearchReport Domain Model ──────────────────────────────────────────

class ResearchReport(BaseModel):
    """
    Canonical domain model for a completed research report.

    This is the object that:
      - Gets stored as JSONB in research_reports.report_data
      - Is returned via GET /research/{id}
      - Drives frontend rendering (sections are optional typed fields)
      - Is round-trip stable: model_dump(mode='json') → model_validate()

    NOT the OpenAI output model — that is SynthesisOutput below.
    This model is constructed by the synthesizer service after post-processing
    the SynthesisOutput with source attribution and provenance metadata.
    """

    schema_version: Literal["1.0"] = "1.0"
    query: str
    generated_at: str                         # ISO datetime string
    processing_time_ms: int | None = None

    # Company cards (always present, one per queried company)
    companies: list[CompanySnapshot] = Field(default_factory=list)

    # ── Sections (optional — only present when data supports them) ────────────
    executive_summary: str

    # Overview: general narrative for single or multi-company queries
    overview: OverviewSection | None = None

    # Comparison: only present when 2+ companies are in the query
    comparison: ComparisonSection | None = None

    # Per-company earnings (multiple if query spans multiple companies)
    earnings: list[EarningsSection] = Field(default_factory=list)

    # News across all queried companies
    news: NewsSection | None = None

    # Vector retrieval results from SEC filings
    filing_insights: FilingInsightsSection | None = None

    # Risk assessment
    risk: RiskSection | None = None

    # ── Source citation registry ──────────────────────────────────────────────
    # All source_ids in sections and company snapshots reference entries here.
    sources: list[SourceAttribution] = Field(default_factory=list)

    # ── Transparency ──────────────────────────────────────────────────────────
    # What the system could not retrieve — rendered as warning banners.
    data_gaps: list[DataGap] = Field(default_factory=list)

    # ── Provenance ────────────────────────────────────────────────────────────
    generation_context: GenerationContext | None = None

    def add_source(self, source: SourceAttribution) -> None:
        """Append a source to the registry. Used by the synthesizer post-processor."""
        # ResearchReport is not frozen — sources are built up during post-processing
        self.sources.append(source)

    def source_id_for(self, ticker: str | None, source_type: SourceType) -> str | None:
        """Convenience lookup: find the first source_id matching ticker + type."""
        for s in self.sources:
            if s.type == source_type and (ticker is None or s.ticker == ticker):
                return s.id
        return None

    @classmethod
    def empty_for(cls, query: str) -> "ResearchReport":
        """Factory for a minimal ResearchReport skeleton — used by the synthesizer."""
        return cls(
            query=query,
            generated_at=datetime.now(tz=timezone.utc).isoformat(),
            executive_summary="",
        )


# ══════════════════════════════════════════════════════════════════════════════
# OpenAI Structured Output Models
# These are passed directly to client.beta.chat.completions.parse(response_format=)
# Rules:
#   - No discriminated unions
#   - All optional fields use T | None with default=None
#   - All list fields use default_factory=list
#   - ConfigDict enforces additionalProperties=False
#   - Use primitive types only (str, float, int, bool, list, None)
#   - Enums: str values only (no complex enum types in nested positions)
# ══════════════════════════════════════════════════════════════════════════════

class SynthesisMetricValue(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"additionalProperties": False},
    )

    ticker: str
    value: float | None = None
    formatted_value: str           # Pre-formatted: "$22.1B", "68.2x"


class SynthesisComparisonMetric(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"additionalProperties": False},
    )

    metric_name: str
    unit: str
    values: list[SynthesisMetricValue]
    winner_ticker: str | None = None
    insight: str


class SynthesisCompanyData(BaseModel):
    """
    Per-company data that the synthesizer extracts from tool results.
    OpenAI repackages the raw tool data into this structure with added analysis.
    """

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"additionalProperties": False},
    )

    ticker: str
    name: str
    exchange: str | None = None
    sector: str | None = None
    description: str | None = None

    # Financial metrics — populated from market data tool results
    current_price: float | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    revenue_ttm: float | None = None
    eps: float | None = None
    change_1d_pct: float | None = None
    change_1m_pct: float | None = None

    # Sentiment — populated from sentiment tool results
    overall_sentiment: str | None = None    # "positive" | "negative" | "neutral"
    sentiment_score: float | None = None    # -1.0 to 1.0
    article_count: int | None = None


class SynthesisEarningsData(BaseModel):
    """Earnings analysis for a single company from filing context."""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"additionalProperties": False},
    )

    ticker: str
    period: str                             # "Q3 FY2024"
    narrative: str                          # AI-written earnings analysis
    revenue: float | None = None
    revenue_growth_yoy_pct: float | None = None
    eps_actual: float | None = None
    beat_miss: str | None = None            # "beat" | "miss" | "in_line"
    guidance: str | None = None


class SynthesisNewsItem(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"additionalProperties": False},
    )

    ticker: str
    title: str
    summary: str                            # Max 2 sentences
    sentiment: str                          # "positive" | "negative" | "neutral"
    published_at: str                       # ISO datetime string
    source_name: str


class SynthesisFilingExcerpt(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"additionalProperties": False},
    )

    ticker: str
    text: str
    document_title: str
    relevance_score: float


class SynthesisRiskFactor(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"additionalProperties": False},
    )

    category: str      # RiskCategory value: "market" | "competitive" | etc.
    title: str
    description: str
    severity: str      # "low" | "medium" | "high"


class SynthesisDataGap(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"additionalProperties": False},
    )

    section_type: str
    ticker: str | None = None
    reason: str
    severity: str      # "warning" | "error"


class SynthesisOutput(BaseModel):
    """
    PRIMARY OpenAI structured output model for the Synthesizer.

    Passed to: client.beta.chat.completions.parse(response_format=SynthesisOutput)

    Design constraints:
      - All fields typed with no complex Union types
      - OpenAI generates this from the synthesis context (tool results + query)
      - Post-processed by the synthesizer service to produce ResearchReport
        (source attribution, provenance, and section wrappers are added then)

    The synthesizer system prompt instructs OpenAI to:
      - Populate companies[] with data from market_data and sentiment tools
      - Leave comparison_metrics[] empty for single-company queries
      - Only populate earnings_analyses[] if filing/earnings data was provided
      - Set data_gaps[] for any tool that failed or returned no data
      - Never fabricate financial figures not present in the provided context
    """

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"additionalProperties": False},
    )

    # Always present
    executive_summary: str

    # Per-company structured data (one entry per ticker in the plan)
    companies: list[SynthesisCompanyData] = Field(default_factory=list)

    # Overview narrative — always present, general analysis
    overview_narrative: str | None = None
    overview_key_points: list[str] = Field(default_factory=list)

    # Comparison — only for multi-company queries
    comparison_metrics: list[SynthesisComparisonMetric] = Field(default_factory=list)
    comparison_commentary: str | None = None

    # Earnings — one per ticker with filing context
    earnings_analyses: list[SynthesisEarningsData] = Field(default_factory=list)

    # News — representative articles for all companies
    news_items: list[SynthesisNewsItem] = Field(default_factory=list)

    # Filing excerpts — from vector retrieval
    filing_excerpts: list[SynthesisFilingExcerpt] = Field(default_factory=list)

    # Risk assessment
    overall_risk_level: str | None = None    # "low" | "medium" | "high"
    risk_factors: list[SynthesisRiskFactor] = Field(default_factory=list)
    risk_summary: str | None = None

    # Transparency — gaps in data coverage
    data_gaps: list[SynthesisDataGap] = Field(default_factory=list)