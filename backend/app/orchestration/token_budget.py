"""
app/orchestration/token_budget.py

Token budget management for the synthesis call.

The synthesizer has a fixed input token budget. This manager ensures
tool results are truncated to fit within that budget while preserving
the highest-value data (highest-confidence, most recent, most relevant).

Architecture constraints from the spec:
  Total synthesis input cap: 8,000 tokens
  ├── System prompt (fixed):   ~900 tokens
  ├── Query + plan context:    ~300 tokens
  ├── Tool results (variable): 6,500 tokens ← this module manages this
  └── Overhead + formatting:   ~300 tokens

Tool result budget allocation (when all tools succeed):
  market_data:       600 tokens  — never truncate (structured, compact data)
  news articles:   2,000 tokens  — top 8 by recency, 250 tokens each
  vector chunks:   1,500 tokens  — top 5 by relevance score, 300 tokens each
  sentiment:         200 tokens  — never truncate (compact summary)
  overhead buffer:   200 tokens

Priority order for budget allocation when over budget:
  1. market_data   (always kept — structured and compact)
  2. sentiment     (always kept — very small)
  3. news          (truncate by reducing article count)
  4. vector        (truncate by reducing chunk count)
"""
from __future__ import annotations

import json
import structlog
from dataclasses import dataclass, field

import tiktoken

from app.tools.base import (
    ToolResult,
    ToolStatus,
    NewsPayload,
    VectorPayload,
    MarketDataPayload,
    SentimentPayload,
    NewsArticle,
    DocumentChunk,
)

log = structlog.get_logger(__name__)

# ── Budget constants ──────────────────────────────────────────────────────────

SYNTHESIS_INPUT_TOKEN_LIMIT = 8_000
SYNTHESIS_OUTPUT_TOKEN_LIMIT = 4_000

# Estimated fixed cost (system prompt + query + formatting overhead)
# Measured once at development time; update if prompts change significantly
FIXED_CONTEXT_TOKENS = 1_200

# Available for tool results
TOOL_RESULTS_BUDGET = SYNTHESIS_INPUT_TOKEN_LIMIT - FIXED_CONTEXT_TOKENS

# Per-tool budget caps
TOOL_BUDGETS: dict[str, int] = {
    "market_data": 700,
    "sentiment_analysis": 250,
    "news_search": 2_000,
    "vector_retrieval": 1_600,
}

# Priority order — lower index = higher priority = preserved when budget is tight
TOOL_PRIORITY: list[str] = [
    "market_data",
    "sentiment_analysis",
    "news_search",
    "vector_retrieval",
]

# Article / chunk limits
MAX_ARTICLES_TO_SYNTHESIZER = 8
MAX_CHUNKS_TO_SYNTHESIZER = 5
MAX_TOKENS_PER_ARTICLE = 250
MAX_TOKENS_PER_CHUNK = 300

# Encoding for tiktoken — cl100k_base is used by claude-sonnet models
ENCODING_NAME = "cl100k_base"


@dataclass
class BudgetAllocation:
    """Result of the budget fitting operation."""

    fitted_results: list[ToolResult]
    total_tokens_estimated: int
    articles_kept: int | None = None
    chunks_kept: int | None = None
    truncated_tools: list[str] = field(default_factory=list)
    over_budget: bool = False


class TokenBudgetManager:
    """
    Counts tokens and truncates tool results to fit within the synthesis budget.

    Uses tiktoken (cl100k_base) which is a reasonable approximation for
    Claude's tokenizer. Actual Claude token counts may differ by ±5%.
    We add a safety margin in the budget constants to account for this.
    """

    def __init__(self) -> None:
        try:
            self._encoder = tiktoken.get_encoding(ENCODING_NAME)
        except Exception as exc:
            log.warning(
                "token_budget.encoder_init_failed",
                encoding=ENCODING_NAME,
                error=str(exc),
            )
            # Fallback: rough character-based estimate (4 chars ≈ 1 token)
            self._encoder = None  # type: ignore[assignment]

    def count(self, text: str) -> int:
        """Count tokens in a text string."""
        if self._encoder is None:
            return len(text) // 4  # fallback approximation
        try:
            return len(self._encoder.encode(text))
        except Exception:
            return len(text) // 4

    def count_dict(self, data: dict | list) -> int:
        """Count tokens in a JSON-serialisable object."""
        return self.count(json.dumps(data, default=str))

    def fit_tool_results(
        self,
        results: list[ToolResult],
        available_budget: int = TOOL_RESULTS_BUDGET,
    ) -> BudgetAllocation:
        """
        Truncates tool results to fit within the available token budget.

        Algorithm:
          1. Sort tools by priority (market_data first, vector last)
          2. For each tool in priority order:
             a. Serialise the full result
             b. If it fits: include it, subtract from budget
             c. If it doesn't fit: attempt partial truncation
                (reduce articles/chunks count)
             d. If truncated version fits: include it, record truncation
             e. If nothing fits: skip the tool, record as truncated

        Returns a BudgetAllocation with the fitted results and metadata.
        """
        # Sort by priority
        priority_map = {tool: i for i, tool in enumerate(TOOL_PRIORITY)}
        sorted_results = sorted(
            results,
            key=lambda r: priority_map.get(r.tool, 99),
        )

        fitted: list[ToolResult] = []
        remaining = available_budget
        truncated_tools: list[str] = []
        articles_kept: int | None = None
        chunks_kept: int | None = None

        for result in sorted_results:
            if not result.has_data:
                # Failed tools don't consume budget — still include for data_gaps
                fitted.append(result)
                continue

            # Try to fit the full result first
            serialised = self._serialise_result(result)
            token_count = self.count(serialised)

            if token_count <= remaining:
                fitted.append(result)
                remaining -= token_count
                log.debug(
                    "token_budget.tool_fitted",
                    tool=result.tool,
                    tokens=token_count,
                    remaining_after=remaining,
                )
                continue

            # Doesn't fit whole — try partial truncation
            truncated_result = self._truncate_result(result, remaining)
            if truncated_result is not None:
                truncated_serialised = self._serialise_result(truncated_result)
                truncated_tokens = self.count(truncated_serialised)

                if truncated_tokens <= remaining:
                    fitted.append(truncated_result)
                    remaining -= truncated_tokens
                    truncated_tools.append(result.tool)

                    # Record how many items were kept
                    if result.tool == "news_search" and isinstance(
                        truncated_result.data, NewsPayload
                    ):
                        articles_kept = len(truncated_result.data.articles)
                    elif result.tool == "vector_retrieval" and isinstance(
                        truncated_result.data, VectorPayload
                    ):
                        chunks_kept = len(truncated_result.data.chunks)

                    log.info(
                        "token_budget.tool_truncated",
                        tool=result.tool,
                        original_tokens=token_count,
                        truncated_tokens=truncated_tokens,
                        remaining_after=remaining,
                    )
                    continue

            # Cannot fit even truncated — skip this tool
            log.warning(
                "token_budget.tool_dropped",
                tool=result.tool,
                token_count=token_count,
                budget_remaining=remaining,
            )
            # Still add as a FAILED result so the synthesizer knows it's missing
            fitted.append(
                ToolResult(
                    tool=result.tool,
                    status=ToolStatus.FAILED,
                    data=None,
                    confidence=result.confidence,
                    error="Tool result dropped: exceeded token budget",
                    duration_ms=result.duration_ms,
                )
            )
            truncated_tools.append(result.tool)

        total_used = available_budget - remaining
        over_budget = remaining < 0

        log.info(
            "token_budget.fit_complete",
            tools_fitted=len(fitted),
            total_tokens_estimated=total_used,
            truncated_tools=truncated_tools,
            budget_remaining=remaining,
            over_budget=over_budget,
        )

        return BudgetAllocation(
            fitted_results=fitted,
            total_tokens_estimated=total_used,
            articles_kept=articles_kept,
            chunks_kept=chunks_kept,
            truncated_tools=truncated_tools,
            over_budget=over_budget,
        )

    def _serialise_result(self, result: ToolResult) -> str:
        """Convert a ToolResult to the string representation sent to the LLM."""
        if not result.has_data:
            return f"[{result.tool.upper()}] FAILED: {result.error}\n"

        header = (
            f"\n[{result.tool.upper()}] {result.confidence.prompt_annotation}\n"
            f"{'─' * 40}\n"
        )

        if result.tool == "market_data" and isinstance(result.data, MarketDataPayload):
            body = self._format_market_data(result.data)
        elif result.tool == "news_search" and isinstance(result.data, NewsPayload):
            body = self._format_news(result.data)
        elif result.tool == "vector_retrieval" and isinstance(result.data, VectorPayload):
            body = self._format_vector(result.data)
        elif result.tool == "sentiment_analysis" and isinstance(result.data, SentimentPayload):
            body = self._format_sentiment(result.data)
        else:
            body = json.dumps(result.data, default=str)

        return header + body + "\n"

    @staticmethod
    def _format_market_data(data: MarketDataPayload) -> str:
        lines = [f"Source: {data.source_name}"]
        for ticker, metrics in data.companies.items():
            lines.append(f"\n{ticker} — {metrics.company_name}")
            if metrics.exchange:
                lines.append(f"  Exchange: {metrics.exchange}")
            if metrics.sector:
                lines.append(f"  Sector: {metrics.sector}")
            if metrics.current_price is not None:
                lines.append(f"  Price: ${metrics.current_price:,.2f}")
            if metrics.change_percent_1d is not None:
                lines.append(f"  1-day change: {metrics.change_percent_1d:+.2f}%")
            if metrics.change_percent_1m is not None:
                lines.append(f"  1-month change: {metrics.change_percent_1m:+.2f}%")
            if metrics.market_cap is not None:
                lines.append(f"  Market cap: ${metrics.market_cap:,.0f}")
            if metrics.pe_ratio is not None:
                lines.append(f"  P/E ratio: {metrics.pe_ratio:.1f}x")
            if metrics.revenue_ttm is not None:
                lines.append(f"  Revenue (TTM): ${metrics.revenue_ttm:,.0f}")
            if metrics.eps is not None:
                lines.append(f"  EPS: ${metrics.eps:.2f}")
            if metrics.volume is not None:
                lines.append(f"  Volume: {metrics.volume:,}")
            # Price history is compact — include just open/close for last 5 days
            if metrics.price_history:
                lines.append(f"  Price history (last {len(metrics.price_history)} days):")
                for pt in metrics.price_history[-5:]:
                    lines.append(f"    {pt.date}: ${pt.close:.2f}")
        return "\n".join(lines)

    @staticmethod
    def _format_news(data: NewsPayload) -> str:
        lines = [f"Articles fetched for: {', '.join(data.tickers_covered)}"]
        for article in data.articles:
            lines.append(
                f"\n[{article.ticker}] {article.published_at.strftime('%Y-%m-%d')} "
                f"— {article.source_name}"
            )
            lines.append(f"  Title: {article.title}")
            lines.append(f"  Summary: {article.description}")
            lines.append(f"  URL: {article.url}")
            lines.append(f"  Article ID: {article.id}")
        return "\n".join(lines)

    @staticmethod
    def _format_vector(data: VectorPayload) -> str:
        lines = [f"Semantic query: {data.query_used}"]
        for chunk in data.chunks:
            lines.append(
                f"\n[{chunk.ticker}] {chunk.document_title} "
                f"(relevance: {chunk.relevance_score:.2f})"
            )
            lines.append(f"  Type: {chunk.document_type}")
            lines.append(f"  Chunk ID: {chunk.id}")
            lines.append(f"  Text:\n    {chunk.text[:600]}")
        return "\n".join(lines)

    @staticmethod
    def _format_sentiment(data: SentimentPayload) -> str:
        lines = ["Company sentiment summaries:"]
        for summary in data.company_summaries:
            lines.append(
                f"  {summary.ticker}: {summary.overall} "
                f"(score: {summary.score:+.3f}, "
                f"articles: {summary.article_count})"
            )
        return "\n".join(lines)

    def _truncate_result(self, result: ToolResult, budget: int) -> ToolResult | None:
        """
        Attempt to create a truncated copy of the tool result that fits in budget.
        Returns None if the result cannot be truncated (e.g., not a list-based payload).
        """
        if result.tool == "news_search" and isinstance(result.data, NewsPayload):
            return self._truncate_news(result, budget)
        if result.tool == "vector_retrieval" and isinstance(result.data, VectorPayload):
            return self._truncate_vector(result, budget)
        # market_data and sentiment cannot be meaningfully truncated
        return None

    def _truncate_news(self, result: ToolResult, budget: int) -> ToolResult | None:
        """Reduce article count until the payload fits within budget."""
        assert isinstance(result.data, NewsPayload)
        articles = list(result.data.articles)

        # Try reducing from MAX down to 1
        for count in range(min(len(articles), MAX_ARTICLES_TO_SYNTHESIZER), 0, -1):
            truncated_data = NewsPayload(
                articles=articles[:count],
                tickers_covered=result.data.tickers_covered,
            )
            truncated_result = ToolResult(
                tool=result.tool,
                status=result.status,
                data=truncated_data,
                confidence=result.confidence,
                error=result.error,
                duration_ms=result.duration_ms,
            )
            serialised = self._serialise_result(truncated_result)
            if self.count(serialised) <= budget:
                return truncated_result

        return None

    def _truncate_vector(self, result: ToolResult, budget: int) -> ToolResult | None:
        """Reduce chunk count (already sorted by relevance) until it fits."""
        assert isinstance(result.data, VectorPayload)
        chunks = list(result.data.chunks)  # Already sorted by relevance desc

        for count in range(min(len(chunks), MAX_CHUNKS_TO_SYNTHESIZER), 0, -1):
            truncated_data = VectorPayload(
                chunks=chunks[:count],
                query_used=result.data.query_used,
            )
            truncated_result = ToolResult(
                tool=result.tool,
                status=result.status,
                data=truncated_data,
                confidence=result.confidence,
                error=result.error,
                duration_ms=result.duration_ms,
            )
            serialised = self._serialise_result(truncated_result)
            if self.count(serialised) <= budget:
                return truncated_result

        return None

    def format_tool_results_for_synthesis(self, results: list[ToolResult]) -> str:
        """
        Serialise all fitted tool results into the formatted string
        that is injected into the synthesizer's user message.
        """
        parts = []
        for result in results:
            parts.append(self._serialise_result(result))
        return "\n".join(parts)