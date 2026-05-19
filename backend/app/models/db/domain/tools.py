"""
Tool Domain Models
===================
Defines the input/output type contracts for all four tools in the pipeline:
  - MarketDataTool  → MarketDataResult
  - NewsSearchTool  → NewsSearchResult
  - SentimentTool   → SentimentResult (OpenAI-structured output)
  - SECFilingTool   → SECFilingResult (from ChromaDB vector retrieval)

All results carry a ToolConfidence object used by the synthesizer
to calibrate how authoritatively it cites each data source.

ToolDispatchResult aggregates successful and failed results
from the parallel dispatcher run.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


# ── Enums ──────────────────────────────────────────────────────────────────────

class ToolName(str, Enum):
    MARKET_DATA = "market_data"
    NEWS_SEARCH = "news_search"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    SEC_FILINGS = "sec_filings"

    # Internal alias: vector retrieval is how SEC filings are fetched
    # Both names map to the same tool implementation
    VECTOR_RETRIEVAL = "vector_retrieval"

    @classmethod
    def allowed_names(cls) -> frozenset[str]:
        return frozenset(m.value for m in cls)


# Sentinel set used by the Planner validator
ALLOWED_TOOL_NAMES: frozenset[str] = ToolName.allowed_names()


class ConfidenceLevel(str, Enum):
    HIGH = "high"       # score >= 0.80
    MEDIUM = "medium"   # score >= 0.55
    LOW = "low"         # score < 0.55

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        if score >= 0.80:
            return cls.HIGH
        if score >= 0.55:
            return cls.MEDIUM
        return cls.LOW


# ── Tool Confidence ────────────────────────────────────────────────────────────

class ToolConfidence(BaseModel):
    """
    Confidence metadata for a tool result.
    Injected into the synthesis context as explicit annotations.
    The Synthesizer system prompt instructs different citation styles per level:
      HIGH   → cite precisely with exact numbers
      MEDIUM → cite with temporal caveat ("as of [date]")
      LOW    → note uncertainty or omit if below threshold
    """

    model_config = ConfigDict(frozen=True)

    score: float                          # 0.0 – 1.0
    level: ConfidenceLevel
    factors: list[str]                    # Human-readable reasons
    data_age_seconds: int | None = None   # Staleness in seconds

    @classmethod
    def high(cls, factors: list[str], age_seconds: int | None = None) -> "ToolConfidence":
        return cls(
            score=0.92,
            level=ConfidenceLevel.HIGH,
            factors=factors,
            data_age_seconds=age_seconds,
        )

    @classmethod
    def medium(cls, factors: list[str], age_seconds: int | None = None) -> "ToolConfidence":
        return cls(
            score=0.68,
            level=ConfidenceLevel.MEDIUM,
            factors=factors,
            data_age_seconds=age_seconds,
        )

    @classmethod
    def low(cls, factors: list[str], age_seconds: int | None = None) -> "ToolConfidence":
        return cls(
            score=0.35,
            level=ConfidenceLevel.LOW,
            factors=factors,
            data_age_seconds=age_seconds,
        )

    @classmethod
    def failed(cls) -> "ToolConfidence":
        return cls(
            score=0.0,
            level=ConfidenceLevel.LOW,
            factors=["Tool execution failed"],
        )


# ── Market Data Tool ───────────────────────────────────────────────────────────

class HistoricalPricePoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    date: str       # ISO date: "2025-05-10"
    close: float
    volume: int
    change_pct: float | None = None


class CompanyMarketData(BaseModel):
    """Market data for a single company. Populated by MarketDataTool."""

    model_config = ConfigDict(frozen=True)

    ticker: str
    company_name: str
    exchange: str | None = None
    sector: str | None = None
    description: str | None = None

    # Current price data
    current_price: float | None = None
    currency: str = "USD"
    market_cap: float | None = None
    pe_ratio: float | None = None
    revenue_ttm: float | None = None
    eps: float | None = None
    dividend_yield: float | None = None
    beta: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None

    # Price change
    change_1d_pct: float | None = None
    change_1w_pct: float | None = None
    change_1m_pct: float | None = None
    volume: int | None = None
    avg_volume_30d: int | None = None

    # Historical — used for chart rendering (30 days max)
    historical_prices: list[HistoricalPricePoint] = Field(default_factory=list)

    # Data provenance
    data_source: str = "yahoo_finance"        # "yahoo_finance" | "alpha_vantage" | "mock"
    fetched_at: str = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc).isoformat()
    )
    is_delayed: bool = False
    delay_minutes: int = 0


class MarketDataResult(BaseModel):
    """Aggregated market data for all requested tickers."""

    model_config = ConfigDict(frozen=True)

    tool: ToolName = ToolName.MARKET_DATA
    status: str     # "success" | "partial" | "failed"
    confidence: ToolConfidence

    # Key: ticker symbol, value: company data
    companies: dict[str, CompanyMarketData] = Field(default_factory=dict)
    failed_tickers: list[str] = Field(default_factory=list)
    error_message: str | None = None
    duration_ms: float | None = None


# ── News Search Tool ───────────────────────────────────────────────────────────

class NewsArticle(BaseModel):
    """A single news article from the news search tool."""

    model_config = ConfigDict(frozen=True)

    id: str                              # Stable ID for reference (hash of url)
    ticker: str                          # Which company this article is about
    title: str
    description: str                     # Article snippet/description
    url: str
    published_at: str                    # ISO datetime string
    source_name: str
    source_domain: str | None = None
    image_url: str | None = None
    language: str = "en"


class NewsSearchResult(BaseModel):
    """All news articles fetched for the requested tickers."""

    model_config = ConfigDict(frozen=True)

    tool: ToolName = ToolName.NEWS_SEARCH
    status: str
    confidence: ToolConfidence

    articles: list[NewsArticle] = Field(default_factory=list)
    # Key: ticker, value: count of articles
    article_counts: dict[str, int] = Field(default_factory=dict)
    failed_tickers: list[str] = Field(default_factory=list)
    data_source: str = "news_api"         # "news_api" | "mock"
    error_message: str | None = None
    duration_ms: float | None = None


# ── Sentiment Analysis Tool (OpenAI-backed) ────────────────────────────────────

class ArticleSentimentResult(BaseModel):
    """Sentiment classification for a single article."""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"additionalProperties": False},
    )

    article_id: str
    sentiment: str                        # "positive" | "negative" | "neutral"
    confidence: float                     # 0.0 – 1.0
    key_themes: list[str]                 # Up to 3 key themes identified


class CompanySentimentSummary(BaseModel):
    """Aggregated sentiment across all articles for a single company."""

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"additionalProperties": False},
    )

    ticker: str
    overall_sentiment: str                # "positive" | "negative" | "neutral"
    sentiment_score: float                # -1.0 to 1.0 weighted average
    article_count: int
    positive_count: int
    negative_count: int
    neutral_count: int
    key_themes: list[str]                 # Top recurring themes across all articles
    sentiment_rationale: str             # One-sentence AI explanation of the overall sentiment


class SentimentAnalysisOutput(BaseModel):
    """
    Direct structured output from OpenAI for the Sentiment tool.

    Passed to: client.beta.chat.completions.parse(response_format=SentimentAnalysisOutput)

    The system prompt instructs OpenAI to classify each article's sentiment
    and then aggregate per company. Input is the news articles (trimmed to budget).
    """

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={"additionalProperties": False},
    )

    company_summaries: list[CompanySentimentSummary] = Field(default_factory=list)
    article_sentiments: list[ArticleSentimentResult] = Field(default_factory=list)


class SentimentResult(BaseModel):
    """Sentiment analysis results, wrapping the OpenAI SentimentAnalysisOutput."""

    model_config = ConfigDict(frozen=True)

    tool: ToolName = ToolName.SENTIMENT_ANALYSIS
    status: str
    confidence: ToolConfidence

    output: SentimentAnalysisOutput | None = None
    articles_analyzed: int = 0
    input_tokens_used: int = 0
    output_tokens_used: int = 0
    error_message: str | None = None
    duration_ms: float | None = None


# ── SEC Filing Tool (ChromaDB Vector Retrieval) ────────────────────────────────

class DocumentChunk(BaseModel):
    """A single chunk from a retrieved SEC filing or earnings document."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str                         # ChromaDB document ID
    ticker: str
    text: str                             # The actual chunk content
    document_title: str                   # "NVIDIA 10-K FY2024", "NVIDIA Q3 2024 Earnings Call"
    document_type: str                    # "10-K" | "10-Q" | "earnings_call" | "8-K"
    period: str | None = None             # "Q3 2024", "FY2024"
    relevance_score: float                # Cosine similarity: 0.0 – 1.0
    chunk_index: int | None = None        # Position in the source document
    source_url: str | None = None


class SECFilingResult(BaseModel):
    """Vector retrieval results for SEC filings and earnings documents."""

    model_config = ConfigDict(frozen=True)

    tool: ToolName = ToolName.SEC_FILINGS
    status: str                           # "success" | "empty" | "failed"
    confidence: ToolConfidence

    chunks: list[DocumentChunk] = Field(default_factory=list)
    query_used: str                       # The semantic query sent to ChromaDB
    collection_name: str = "financial_docs"
    total_chunks_retrieved: int = 0
    error_message: str | None = None
    duration_ms: float | None = None


# ── Tool Failure Record ────────────────────────────────────────────────────────

class ToolFailure(BaseModel):
    """Record of a tool execution failure. One per failed tool call."""

    model_config = ConfigDict(frozen=True)

    tool_name: str
    tickers: list[str]
    error_type: str               # "timeout" | "api_error" | "validation_error" | "unknown"
    error_message: str
    duration_ms: float | None = None
    retried: bool = False
    retry_count: int = 0


# ── Dispatch Result Aggregate ──────────────────────────────────────────────────

class ToolDispatchResult(BaseModel):
    """
    Aggregated result from the Parallel Tool Dispatcher.

    Contains all successful tool results and all failures.
    The Synthesizer receives this and builds its context from successful results.
    The Coordinator uses failures to populate data_gaps and determine
    whether to proceed to synthesis (PARTIAL_SUCCESS path) or abort (FAILED).

    Minimum requirement to proceed to synthesis:
      At least one successful tool result must be present.
      If ALL tools fail, the report transitions to FAILED immediately.
    """

    model_config = ConfigDict(frozen=True)

    # Successful results — present in the synthesis context
    market_data: MarketDataResult | None = None
    news_search: NewsSearchResult | None = None
    sentiment: SentimentResult | None = None
    sec_filings: SECFilingResult | None = None

    # Failure records — used for data_gaps population
    failures: list[ToolFailure] = Field(default_factory=list)

    # Timing
    started_at: str
    completed_at: str
    duration_ms: float

    @property
    def has_any_success(self) -> bool:
        return any([
            self.market_data is not None,
            self.news_search is not None,
            self.sentiment is not None,
            self.sec_filings is not None,
        ])

    @property
    def is_partial(self) -> bool:
        """True if some tools succeeded and some failed."""
        success_count = sum([
            self.market_data is not None,
            self.news_search is not None,
            self.sentiment is not None,
            self.sec_filings is not None,
        ])
        return success_count > 0 and len(self.failures) > 0

    @property
    def successful_tool_names(self) -> list[str]:
        names = []
        if self.market_data is not None:
            names.append(ToolName.MARKET_DATA.value)
        if self.news_search is not None:
            names.append(ToolName.NEWS_SEARCH.value)
        if self.sentiment is not None:
            names.append(ToolName.SENTIMENT_ANALYSIS.value)
        if self.sec_filings is not None:
            names.append(ToolName.SEC_FILINGS.value)
        return names

    @property
    def failed_tool_names(self) -> list[str]:
        return [f.tool_name for f in self.failures]