"""
app/clients/market_data_client.py

Raw market data fetching with a three-tier fallback strategy:

  Tier 1: yfinance (Yahoo Finance) — free, no API key, reliable for demo
  Tier 2: Alpha Vantage — free tier, 25 calls/day, requires ALPHA_VANTAGE_KEY
  Tier 3: Mock data — deterministic, seeded from real-ish values for demo

The client returns raw data dictionaries that the MarketDataTool converts
into typed CompanyMetrics objects.

Design decisions:
  - yfinance is synchronous; we run it in a thread pool to stay async
  - Alpha Vantage is called via httpx (async)
  - Mock data is pre-seeded with realistic values for 5 key tickers
  - All tiers return the same dict structure — tool doesn't know which tier ran
"""
from __future__ import annotations

import asyncio
import os
from datetime import date, datetime, timedelta, timezone
from typing import Any

import structlog

log = structlog.get_logger(__name__)

# ── Mock data seed (fallback of last resort) ──────────────────────────────────

_MOCK_DATA: dict[str, dict[str, Any]] = {
    "NVDA": {
        "ticker": "NVDA",
        "company_name": "NVIDIA Corporation",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "description": (
            "NVIDIA Corporation designs, develops, and markets graphics processing units (GPUs) "
            "and system-on-chip units. The company serves the gaming, professional visualization, "
            "data center, and automotive markets."
        ),
        "current_price": 875.40,
        "market_cap": 2_150_000_000_000,
        "pe_ratio": 68.2,
        "revenue_ttm": 79_774_000_000,
        "eps": 12.85,
        "change_percent_1d": 2.31,
        "change_percent_1m": 12.7,
        "volume": 41_200_000,
        "is_mock": True,
    },
    "AMD": {
        "ticker": "AMD",
        "company_name": "Advanced Micro Devices, Inc.",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "description": (
            "Advanced Micro Devices designs and produces microprocessors, GPUs, and related "
            "semiconductor products for data centres, embedded systems, game consoles, and PCs."
        ),
        "current_price": 142.80,
        "market_cap": 231_000_000_000,
        "pe_ratio": 38.1,
        "revenue_ttm": 22_680_000_000,
        "eps": 3.75,
        "change_percent_1d": -0.82,
        "change_percent_1m": -5.3,
        "volume": 28_600_000,
        "is_mock": True,
    },
    "AAPL": {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "description": (
            "Apple Inc. designs, manufactures, and markets smartphones, personal computers, "
            "tablets, wearables, and accessories, and sells a variety of related services."
        ),
        "current_price": 189.30,
        "market_cap": 2_920_000_000_000,
        "pe_ratio": 31.4,
        "revenue_ttm": 385_600_000_000,
        "eps": 6.42,
        "change_percent_1d": 0.47,
        "change_percent_1m": 3.2,
        "volume": 52_300_000,
        "is_mock": True,
    },
    "MSFT": {
        "ticker": "MSFT",
        "company_name": "Microsoft Corporation",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "description": (
            "Microsoft Corporation develops, licenses, and supports software, services, devices, "
            "and solutions worldwide. Products include Windows, Office, Azure, and Xbox."
        ),
        "current_price": 415.20,
        "market_cap": 3_080_000_000_000,
        "pe_ratio": 36.8,
        "revenue_ttm": 245_100_000_000,
        "eps": 11.28,
        "change_percent_1d": 0.63,
        "change_percent_1m": 7.1,
        "volume": 18_900_000,
        "is_mock": True,
    },
    "TSLA": {
        "ticker": "TSLA",
        "company_name": "Tesla, Inc.",
        "exchange": "NASDAQ",
        "sector": "Consumer Cyclical",
        "description": (
            "Tesla designs, develops, manufactures, leases, and sells electric vehicles, "
            "energy generation and storage systems, and related services."
        ),
        "current_price": 172.60,
        "market_cap": 552_000_000_000,
        "pe_ratio": 49.3,
        "revenue_ttm": 97_690_000_000,
        "eps": 3.50,
        "change_percent_1d": -1.24,
        "change_percent_1m": -18.4,
        "volume": 88_700_000,
        "is_mock": True,
    },
}


def _generate_mock_price_history(
    ticker: str,
    base_price: float,
    days: int = 30,
) -> list[dict[str, Any]]:
    """
    Generate deterministic-ish 30-day price history for mock data.
    Uses a simple pseudo-random walk seeded from the ticker string.
    """
    import hashlib
    import math

    seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
    history = []
    price = base_price

    for i in range(days):
        day_date = date.today() - timedelta(days=days - i)
        # Skip weekends
        if day_date.weekday() >= 5:
            continue
        # Pseudo-random daily change based on seed
        angle = (seed + i * 137) % 1000
        change_pct = (math.sin(angle) * 0.015)  # ±1.5% daily swing
        price = price * (1 + change_pct)
        history.append({
            "date": day_date.isoformat(),
            "close": round(price, 2),
            "volume": int(abs(math.sin(seed + i)) * 50_000_000) + 10_000_000,
        })

    return history


class MarketDataClient:
    """
    Fetches market data with a three-tier fallback:
      yfinance → Alpha Vantage → mock data

    Returns a dict with keys matching CompanyMetrics fields (plus is_mock flag).
    Raises no exceptions — always returns data (may be mock).
    """

    def __init__(self) -> None:
        self._alpha_vantage_key = os.environ.get("ALPHA_VANTAGE_KEY", "")

    async def fetch_ticker(self, ticker: str) -> dict[str, Any]:
        """
        Fetch market data for a single ticker.
        Returns the first successful tier's data.
        """
        # Tier 1: yfinance
        try:
            data = await self._fetch_yfinance(ticker)
            if data:
                log.info("market_client.yfinance_success", ticker=ticker)
                return data
        except Exception as exc:
            log.warning("market_client.yfinance_failed", ticker=ticker, error=str(exc))

        # Tier 2: Alpha Vantage
        if self._alpha_vantage_key:
            try:
                data = await self._fetch_alpha_vantage(ticker)
                if data:
                    log.info("market_client.alpha_vantage_success", ticker=ticker)
                    return data
            except Exception as exc:
                log.warning("market_client.alpha_vantage_failed", ticker=ticker, error=str(exc))

        # Tier 3: Mock data
        log.warning(
            "market_client.falling_back_to_mock",
            ticker=ticker,
            alpha_vantage_configured=bool(self._alpha_vantage_key),
        )
        return self._get_mock_data(ticker)

    async def fetch_tickers(self, tickers: list[str]) -> dict[str, dict[str, Any]]:
        """
        Fetch multiple tickers concurrently.
        Returns dict keyed by ticker.
        """
        tasks = [self.fetch_ticker(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: dict[str, dict[str, Any]] = {}
        for ticker, result in zip(tickers, results):
            if isinstance(result, Exception):
                log.error(
                    "market_client.ticker_exception",
                    ticker=ticker,
                    error=str(result),
                )
                output[ticker] = self._get_mock_data(ticker)
            else:
                output[ticker] = result  # type: ignore[assignment]

        return output

    async def _fetch_yfinance(self, ticker: str) -> dict[str, Any] | None:
        """
        Fetch via yfinance in a thread pool (yfinance is synchronous).
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_yfinance_sync, ticker)

    @staticmethod
    def _fetch_yfinance_sync(ticker: str) -> dict[str, Any] | None:
        """Synchronous yfinance fetch — runs in thread pool."""
        try:
            import yfinance as yf  # type: ignore[import]

            stock = yf.Ticker(ticker)
            info = stock.info

            # yfinance returns an empty dict or dict with mostly None if ticker invalid
            if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
                return None

            current_price = info.get("currentPrice") or info.get("regularMarketPrice")

            # Fetch 30-day history
            hist = stock.history(period="1mo")
            price_history = []
            if not hist.empty:
                for idx, row in hist.iterrows():
                    day = idx.date() if hasattr(idx, "date") else idx
                    price_history.append({
                        "date": str(day),
                        "close": round(float(row["Close"]), 2),
                        "volume": int(row.get("Volume", 0)),
                    })

            # 1-month change
            change_1m = None
            if price_history and current_price:
                first_price = price_history[0]["close"]
                if first_price and first_price != 0:
                    change_1m = round(
                        ((current_price - first_price) / first_price) * 100, 2
                    )

            return {
                "ticker": ticker,
                "company_name": info.get("longName") or info.get("shortName") or ticker,
                "exchange": info.get("exchange"),
                "sector": info.get("sector"),
                "description": (info.get("longBusinessSummary") or "")[:500],
                "current_price": round(float(current_price), 2) if current_price else None,
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "revenue_ttm": info.get("totalRevenue"),
                "eps": info.get("trailingEps"),
                "change_percent_1d": info.get("regularMarketChangePercent"),
                "change_percent_1m": change_1m,
                "volume": info.get("regularMarketVolume"),
                "price_history": price_history,
                "is_mock": False,
            }

        except Exception as exc:
            log.warning("yfinance_sync.error", ticker=ticker, error=str(exc))
            return None

    async def _fetch_alpha_vantage(self, ticker: str) -> dict[str, Any] | None:
        """Fetch via Alpha Vantage REST API."""
        import httpx

        url = "https://www.alphavantage.co/query"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": ticker,
            "apikey": self._alpha_vantage_key,
        }

        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        quote = data.get("Global Quote", {})
        if not quote or "05. price" not in quote:
            return None

        current_price = float(quote["05. price"])
        change_pct = float(quote.get("10. change percent", "0").rstrip("%") or 0)

        # Alpha Vantage doesn't provide company info in the free GLOBAL_QUOTE endpoint
        # Use mock data for company details, overlay with real price
        base = self._get_mock_data(ticker)
        base.update({
            "current_price": round(current_price, 2),
            "change_percent_1d": round(change_pct, 2),
            "is_mock": False,
        })
        return base

    def _get_mock_data(self, ticker: str) -> dict[str, Any]:
        """Return mock data for the ticker, or a generic placeholder if unknown."""
        if ticker in _MOCK_DATA:
            data = dict(_MOCK_DATA[ticker])
            base_price = data.get("current_price", 100.0)
            data["price_history"] = _generate_mock_price_history(ticker, base_price)
            return data

        # Generic placeholder for unknown tickers
        log.warning("market_client.unknown_ticker_mock", ticker=ticker)
        return {
            "ticker": ticker,
            "company_name": f"{ticker} Corp.",
            "exchange": "NASDAQ",
            "sector": None,
            "description": None,
            "current_price": None,
            "market_cap": None,
            "pe_ratio": None,
            "revenue_ttm": None,
            "eps": None,
            "change_percent_1d": None,
            "change_percent_1m": None,
            "volume": None,
            "price_history": [],
            "is_mock": True,
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_market_data_client: MarketDataClient | None = None


def get_market_data_client() -> MarketDataClient:
    global _market_data_client
    if _market_data_client is None:
        _market_data_client = MarketDataClient()
    return _market_data_client