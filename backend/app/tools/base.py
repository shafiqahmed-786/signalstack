"""
app/tools/base.py

Base classes for all research tools.

Every tool in the dispatcher implements BaseTool. Every tool returns a ToolResult
with a mandatory ToolConfidence object. The synthesizer consumes confidence
metadata to calibrate how assertively it presents data from each source.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar

import structlog

log = structlog.get_logger(__name__)

T = TypeVar("T")


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class ToolConfidence:
    """
    Represents how reliable a tool's output is.

    score       — 0.0 to 1.0 for programmatic comparison and sorting
    level       — HIGH / MEDIUM / LOW for prompt injection and UI display
    factors     — human-readable list of reasons (injected into synthesis context)
    data_age_s  — seconds since the data was generated/fetched; None if unknown
    """

    score: float
    level: ConfidenceLevel
    factors: list[str]
    data_age_s: int | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Confidence score must be 0.0–1.0, got {self.score}")

    @property
    def prompt_annotation(self) -> str:
        """
        Returns a formatted string for injection into the synthesis context.
        Example:
            ⬤ HIGH CONFIDENCE (score: 0.95)
            Factors: Live data, <15min delay
            Data age: 8 minutes
        """
        dot = {"high": "⬤", "medium": "◐", "low": "○"}[self.level.value]
        age_str = ""
        if self.data_age_s is not None:
            minutes = self.data_age_s // 60
            age_str = f"\nData age: {minutes} minutes" if minutes >= 1 else "\nData age: <1 minute"
        factors_str = ", ".join(self.factors) if self.factors else "Unknown"
        return (
            f"{dot} {self.level.value.upper()} CONFIDENCE (score: {self.score:.2f})\n"
            f"Factors: {factors_str}{age_str}"
        )


class ToolStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"     # Some data returned but incomplete
    EMPTY = "empty"         # No data found (not an error — e.g., no news articles)
    FAILED = "failed"       # Error — no data returned


@dataclass
class ToolResult(Generic[T]):
    """
    Standardised result envelope returned by every tool.

    tool        — tool identifier string (matches ALLOWED_TOOLS)
    status      — outcome classification
    data        — typed payload; None only when status is FAILED
    confidence  — reliability metadata for the synthesizer
    error       — human-readable error description when status is FAILED
    duration_ms — execution time; recorded by the dispatcher wrapper
    """

    tool: str
    status: ToolStatus
    data: T | None
    confidence: ToolConfidence
    error: str | None = None
    duration_ms: int = 0

    @property
    def succeeded(self) -> bool:
        return self.status in (ToolStatus.SUCCESS, ToolStatus.PARTIAL, ToolStatus.EMPTY)

    @property
    def has_data(self) -> bool:
        return self.data is not None and self.status != ToolStatus.FAILED

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "tool": self.tool,
            "status": self.status.value,
            "confidence_level": self.confidence.level.value,
            "confidence_score": self.confidence.score,
            "duration_ms": self.duration_ms,
            "has_data": self.has_data,
            "error": self.error,
        }


# ── Typed data payloads ────────────────────────────────────────────────────────

@dataclass
class PricePoint:
    date: str       # ISO date string "YYYY-MM-DD"
    close: float
    volume: int


@dataclass
class CompanyMetrics:
    ticker: str
    company_name: str
    exchange: str | None
    sector: str | None
    description: str | None
    current_price: float | None
    market_cap: float | None
    pe_ratio: float | None
    revenue_ttm: float | None
    eps: float | None
    change_percent_1d: float | None
    change_percent_1m: float | None
    price_history: list[PricePoint]     # Last 30 days
    volume: int | None
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MarketDataPayload:
    """Payload for MarketDataTool results."""
    companies: dict[str, CompanyMetrics]    # keyed by ticker
    source_name: str = "Yahoo Finance"
    source_url: str | None = None


@dataclass
class NewsArticle:
    id: str
    ticker: str
    title: str
    description: str        # 2–3 sentence summary from NewsAPI
    url: str
    published_at: datetime
    source_name: str
    raw_sentiment_score: float | None = None   # pre-classification if available


@dataclass
class NewsPayload:
    """Payload for NewsSearchTool results."""
    articles: list[NewsArticle]
    tickers_covered: list[str]


@dataclass
class DocumentChunk:
    id: str
    ticker: str
    text: str
    document_title: str     # e.g. "NVIDIA 10-K Q3 2024"
    document_type: str      # "10-K" | "earnings_transcript" | "analyst_report"
    relevance_score: float  # cosine similarity 0.0–1.0
    source_url: str | None = None


@dataclass
class VectorPayload:
    """Payload for VectorRetrievalTool results."""
    chunks: list[DocumentChunk]
    query_used: str


@dataclass
class ArticleSentiment:
    article_id: str
    ticker: str
    sentiment: str          # "positive" | "negative" | "neutral"
    sentiment_score: float  # –1.0 to 1.0
    title: str
    summary: str            # AI-compressed to 2 sentences


@dataclass
class CompanySentimentSummary:
    ticker: str
    overall: str            # "positive" | "negative" | "neutral"
    score: float            # –1.0 to 1.0 weighted average
    article_count: int


@dataclass
class SentimentPayload:
    """Payload for SentimentTool results."""
    articles: list[ArticleSentiment]
    company_summaries: list[CompanySentimentSummary]


# ── Base Tool ──────────────────────────────────────────────────────────────────

class BaseTool(ABC):
    """
    Abstract base for all research tools.

    Subclasses implement _execute() with their specific logic.
    The execute() wrapper handles:
      - Timing (duration_ms)
      - Structured logging (tool.started, tool.completed, tool.failed)
      - Exception → ToolResult(FAILED) conversion so the dispatcher
        never receives raw exceptions from tool execution
    """

    TOOL_NAME: str = "base"  # Override in each subclass

    async def execute(self, **kwargs: Any) -> ToolResult:
        """
        Public execute wrapper. Do not override — implement _execute() instead.
        """
        start = time.monotonic()
        log.info("tool.started", tool=self.TOOL_NAME, **{k: str(v) for k, v in kwargs.items()})

        try:
            result = await self._execute(**kwargs)
            result.duration_ms = int((time.monotonic() - start) * 1000)
            log.info(
                "tool.completed",
                tool=self.TOOL_NAME,
                status=result.status.value,
                confidence=result.confidence.level.value,
                duration_ms=result.duration_ms,
            )
            return result

        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            log.error(
                "tool.failed",
                tool=self.TOOL_NAME,
                error=str(exc),
                duration_ms=duration_ms,
                exc_info=True,
            )
            return ToolResult(
                tool=self.TOOL_NAME,
                status=ToolStatus.FAILED,
                data=None,
                confidence=ToolConfidence(
                    score=0.0,
                    level=ConfidenceLevel.LOW,
                    factors=[f"Tool execution failed: {type(exc).__name__}"],
                ),
                error=str(exc),
                duration_ms=duration_ms,
            )

    @abstractmethod
    async def _execute(self, **kwargs: Any) -> ToolResult:
        """Override this in each tool subclass."""
        ...