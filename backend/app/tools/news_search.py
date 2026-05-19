"""
app/tools/news_search.py

NewsSearchTool: fetches recent news articles for a list of tickers.

Confidence calculation:
  HIGH   — recent articles (avg age ≤6h)
  MEDIUM — moderately recent (≤48h)
  LOW    — older news (>48h) or seed articles being used

The tool normalises published_at to timezone-aware datetime objects
before passing to the SentimentTool downstream.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from statistics import mean
from typing import Any

import structlog

from app.clients.news_api_client import get_news_api_client
from app.tools.base import (
    BaseTool,
    ConfidenceLevel,
    NewsArticle,
    NewsPayload,
    ToolConfidence,
    ToolResult,
    ToolStatus,
)

log = structlog.get_logger(__name__)

MAX_ARTICLES_TO_FETCH = 20


class NewsSearchTool(BaseTool):
    """
    Fetches recent news articles for the given tickers.

    Returns a ToolResult[NewsPayload] where NewsPayload.articles is a list
    of NewsArticle objects sorted by published_at descending (newest first).
    """

    TOOL_NAME = "news_search"

    async def _execute(
        self,
        tickers: list[str],
        **kwargs: Any,
    ) -> ToolResult[NewsPayload]:
        client = get_news_api_client()

        raw_articles = await client.fetch_articles(
            tickers=tickers,
            max_articles=MAX_ARTICLES_TO_FETCH,
        )

        if not raw_articles:
            return ToolResult(
                tool=self.TOOL_NAME,
                status=ToolStatus.EMPTY,
                data=NewsPayload(articles=[], tickers_covered=tickers),
                confidence=ToolConfidence(
                    score=0.0,
                    level=ConfidenceLevel.LOW,
                    factors=["No news articles found for the requested tickers"],
                ),
            )

        articles: list[NewsArticle] = []
        parse_errors = 0

        for raw in raw_articles:
            try:
                published_at = self._parse_datetime(raw.get("published_at", ""))
                if published_at is None:
                    parse_errors += 1
                    continue

                articles.append(
                    NewsArticle(
                        id=raw.get("id") or str(uuid.uuid4()),
                        ticker=raw.get("ticker", "UNKNOWN").upper(),
                        title=raw.get("title", "").strip(),
                        description=(raw.get("description") or "").strip()[:500],
                        url=raw.get("url", ""),
                        published_at=published_at,
                        source_name=raw.get("source_name", "Unknown"),
                    )
                )
            except Exception as exc:
                parse_errors += 1
                log.debug(
                    "news_tool.article_parse_error",
                    error=str(exc),
                    raw_id=raw.get("id"),
                )

        if parse_errors > 0:
            log.info(
                "news_tool.parse_errors",
                total_raw=len(raw_articles),
                parse_errors=parse_errors,
                parsed_ok=len(articles),
            )

        # Sort by published_at descending (newest first)
        articles.sort(key=lambda a: a.published_at, reverse=True)

        if not articles:
            return ToolResult(
                tool=self.TOOL_NAME,
                status=ToolStatus.EMPTY,
                data=NewsPayload(articles=[], tickers_covered=tickers),
                confidence=ToolConfidence(
                    score=0.0,
                    level=ConfidenceLevel.LOW,
                    factors=["All fetched articles failed to parse"],
                ),
            )

        confidence = self._calculate_confidence(articles)

        return ToolResult(
            tool=self.TOOL_NAME,
            status=ToolStatus.SUCCESS,
            data=NewsPayload(articles=articles, tickers_covered=tickers),
            confidence=confidence,
        )

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        """
        Parse a datetime string to a timezone-aware datetime object.
        Handles ISO 8601 with and without timezone info.
        """
        if not value:
            return None

        # Try common formats
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%d",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(value, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

        # Last resort: dateutil if available
        try:
            from dateutil import parser as dateutil_parser  # type: ignore[import]

            dt = dateutil_parser.parse(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass

        return None

    @staticmethod
    def _calculate_confidence(articles: list[NewsArticle]) -> ToolConfidence:
        """Confidence based on average article recency."""
        now = datetime.now(timezone.utc)

        age_hours: list[float] = []
        for article in articles:
            delta = now - article.published_at
            age_hours.append(delta.total_seconds() / 3600)

        avg_age = mean(age_hours) if age_hours else 999.0
        avg_age_s = int(avg_age * 3600)

        if avg_age <= 6:
            return ToolConfidence(
                score=0.90,
                level=ConfidenceLevel.HIGH,
                factors=[
                    f"Very recent articles (avg {avg_age:.1f}h old)",
                    f"{len(articles)} articles retrieved",
                ],
                data_age_s=avg_age_s,
            )

        if avg_age <= 48:
            return ToolConfidence(
                score=0.68,
                level=ConfidenceLevel.MEDIUM,
                factors=[
                    f"Moderately recent articles (avg {avg_age:.1f}h old)",
                    f"{len(articles)} articles retrieved",
                ],
                data_age_s=avg_age_s,
            )

        return ToolConfidence(
            score=0.40,
            level=ConfidenceLevel.LOW,
            factors=[
                f"Older news articles (avg {avg_age:.0f}h old)",
                "Consider this as background context, not breaking news",
            ],
            data_age_s=avg_age_s,
        )