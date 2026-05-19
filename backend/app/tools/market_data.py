"""
app/tools/market_data.py

MarketDataTool: fetches financial metrics for a list of tickers.

Confidence calculation:
  HIGH   — live data from yfinance (is_mock=False, data fresh)
  MEDIUM — slightly delayed or partial data
  LOW    — mock/fallback data used for any ticker
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from app.clients.market_data_client import get_market_data_client
from app.tools.base import (
    BaseTool,
    CompanyMetrics,
    ConfidenceLevel,
    MarketDataPayload,
    PricePoint,
    ToolConfidence,
    ToolResult,
    ToolStatus,
)

log = structlog.get_logger(__name__)


class MarketDataTool(BaseTool):
    """
    Fetches current market data for a list of ticker symbols.

    Returns a ToolResult[MarketDataPayload] with per-company CompanyMetrics
    objects. The confidence level reflects whether live or mock data was used.
    """

    TOOL_NAME = "market_data"

    async def _execute(
        self,
        tickers: list[str],
        **kwargs: Any,
    ) -> ToolResult[MarketDataPayload]:
        client = get_market_data_client()
        raw_results = await client.fetch_tickers(tickers)

        companies: dict[str, CompanyMetrics] = {}
        any_mock = False
        any_missing = False

        for ticker in tickers:
            raw = raw_results.get(ticker)
            if not raw:
                any_missing = True
                log.warning("market_tool.ticker_missing", ticker=ticker)
                continue

            if raw.get("is_mock", False):
                any_mock = True

            # Build price history
            price_history: list[PricePoint] = []
            for pt in raw.get("price_history", []):
                try:
                    price_history.append(
                        PricePoint(
                            date=str(pt["date"]),
                            close=float(pt["close"]),
                            volume=int(pt.get("volume", 0)),
                        )
                    )
                except (KeyError, ValueError, TypeError) as exc:
                    log.debug(
                        "market_tool.price_point_parse_error",
                        ticker=ticker,
                        error=str(exc),
                    )

            companies[ticker] = CompanyMetrics(
                ticker=ticker,
                company_name=raw.get("company_name") or ticker,
                exchange=raw.get("exchange"),
                sector=raw.get("sector"),
                description=raw.get("description"),
                current_price=self._safe_float(raw.get("current_price")),
                market_cap=self._safe_float(raw.get("market_cap")),
                pe_ratio=self._safe_float(raw.get("pe_ratio")),
                revenue_ttm=self._safe_float(raw.get("revenue_ttm")),
                eps=self._safe_float(raw.get("eps")),
                change_percent_1d=self._safe_float(raw.get("change_percent_1d")),
                change_percent_1m=self._safe_float(raw.get("change_percent_1m")),
                price_history=price_history,
                volume=self._safe_int(raw.get("volume")),
                fetched_at=datetime.now(timezone.utc),
            )

        if not companies:
            return ToolResult(
                tool=self.TOOL_NAME,
                status=ToolStatus.FAILED,
                data=None,
                confidence=ToolConfidence(
                    score=0.0,
                    level=ConfidenceLevel.LOW,
                    factors=["No market data could be retrieved for any ticker"],
                ),
                error=f"Failed to fetch market data for: {', '.join(tickers)}",
            )

        confidence = self._calculate_confidence(any_mock=any_mock, any_missing=any_missing)

        status = ToolStatus.SUCCESS
        if any_missing and companies:
            status = ToolStatus.PARTIAL
        elif any_mock:
            status = ToolStatus.PARTIAL  # Got data but from mock tier

        return ToolResult(
            tool=self.TOOL_NAME,
            status=status,
            data=MarketDataPayload(
                companies=companies,
                source_name="Yahoo Finance" if not any_mock else "Yahoo Finance / Mock Data",
                source_url="https://finance.yahoo.com",
            ),
            confidence=confidence,
        )

    @staticmethod
    def _calculate_confidence(any_mock: bool, any_missing: bool) -> ToolConfidence:
        """Derive confidence based on data source tier."""
        if any_mock:
            return ToolConfidence(
                score=0.35,
                level=ConfidenceLevel.LOW,
                factors=[
                    "Some or all data from fallback mock values",
                    "Metrics reflect approximate typical values, not live data",
                ],
            )

        if any_missing:
            return ToolConfidence(
                score=0.70,
                level=ConfidenceLevel.MEDIUM,
                factors=[
                    "Live data retrieved but some tickers were unavailable",
                    "Partial data — missing tickers listed in data_gaps",
                ],
            )

        return ToolConfidence(
            score=0.92,
            level=ConfidenceLevel.HIGH,
            factors=["Live market data via Yahoo Finance", "Data freshness: <5 minutes"],
            data_age_s=300,
        )

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            result = float(value)
            return None if result != result else result  # Filter NaN
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None