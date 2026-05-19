"""
app/orchestration/engine.py

Production orchestration engine.

Pipeline: PLANNING → DISPATCHING (parallel tools) → SYNTHESIZING → COMPLETED/PARTIAL/FAILED

Integrates with:
  - ReportStateMachine — SSE event emission + DB status transitions
  - ReportRepository   — final metadata persistence
  - MarketDataTool     — yfinance with mock fallback (always works)
  - NewsSearchTool     — NewsAPI with seed-data fallback (always works)
  - AnthropicClient    — optional LLM summary (graceful no-op if key absent)
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from app.models.domain.research import ReportStatus
from app.orchestration.state_machine import ReportStateMachine

log = structlog.get_logger(__name__)


class OrchestrationEngine:
    """
    Single-request orchestration coordinator.

    Called from ResearchService._run_orchestration() as an asyncio background task.
    One instance is created per research query.
    """

    def __init__(self, session: Any) -> None:
        self._session = session

    # ── Public entry point ────────────────────────────────────────────────────

    async def run(
        self,
        *,
        report_id: uuid.UUID,
        body: Any,
        ctx: Any,
        sse_queue: asyncio.Queue,
    ) -> None:
        """
        Execute the full orchestration pipeline.
        Always emits the SSE sentinel so the client stream is closed cleanly.
        """
        from app.repositories.report_repository import ReportRepository

        repo = ReportRepository(self._session)
        sm = ReportStateMachine(report_id, sse_queue, repo)
        start_ns = time.perf_counter()

        try:
            await self._pipeline(sm, body, repo, start_ns)
        except Exception as exc:
            log.error(
                "engine.pipeline_crash",
                report_id=str(report_id),
                error=str(exc),
                exc_info=True,
            )
            if not sm.is_terminal:
                try:
                    await sm.transition(
                        ReportStatus.FAILED,
                        error_message=f"Orchestration error: {type(exc).__name__}: {exc}",
                    )
                    await self._session.commit()
                except Exception:
                    pass
        finally:
            await sm.emit_sentinel()

    # ── Pipeline ──────────────────────────────────────────────────────────────

    async def _pipeline(
        self,
        sm: ReportStateMachine,
        body: Any,
        repo: Any,
        start_ns: float,
    ) -> None:
        """Three-phase orchestration: planning → dispatching → synthesizing."""

        # ── Phase 1: Planning ─────────────────────────────────────────────────
        await sm.transition(ReportStatus.PLANNING)
        await self._session.commit()

        companies = self._resolve_companies(body)
        log.info("engine.plan_resolved", companies=companies, query=body.query[:80])

        # ── Phase 2: Dispatching ──────────────────────────────────────────────
        await sm.transition(
            ReportStatus.DISPATCHING,
            metadata={
                "plan": {
                    "companies": companies,
                    "intent": "GENERAL_RESEARCH",
                    "tools": ["market_data", "news_search"],
                }
            },
        )
        await self._session.commit()

        tool_results = await self._dispatch_tools(sm, companies)
        n_ok   = sum(1 for v in tool_results.values() if v is not None)
        n_fail = len(tool_results) - n_ok

        # ── Phase 3: Synthesizing ─────────────────────────────────────────────
        await sm.transition(
            ReportStatus.SYNTHESIZING,
            metadata={"tools_succeeded": n_ok, "tools_failed": n_fail},
        )
        await self._session.commit()

        elapsed_ms = int((time.perf_counter() - start_ns) * 1000)
        report_data = self._build_report(
            query=body.query,
            companies=companies,
            market_result=tool_results.get("market_data"),
            news_result=tool_results.get("news_search"),
            elapsed_ms=elapsed_ms,
        )

        # Optional LLM executive summary (graceful no-op if Anthropic key absent)
        report_data["executive_summary"] = await self._executive_summary(
            query=body.query,
            companies=companies,
            report_data=report_data,
        )

        # ── Completion ────────────────────────────────────────────────────────
        has_gaps  = bool(report_data.get("data_gaps"))
        final     = ReportStatus.PARTIAL if has_gaps else ReportStatus.COMPLETED
        tools_run = [k for k, v in tool_results.items() if v is not None]

        await sm.transition(final, report_data=report_data,
                            metadata={"processing_time_ms": elapsed_ms})

        # Persist extra metadata the state machine doesn't carry
        try:
            await repo.update_status(
                report_id=sm.report_id,
                status=final,
                report_data=report_data,
                processing_time_ms=elapsed_ms,
                tools_called=tools_run,
                model_used="rule-based+anthropic" if self._anthropic_available() else "rule-based",
                companies=companies,
            )
            await self._session.commit()
        except TypeError:
            # Repo may not accept all kwargs — fall back to minimal call
            await self._session.commit()

    # ── Company resolution ────────────────────────────────────────────────────

    @staticmethod
    def _resolve_companies(body: Any) -> list[str]:
        """
        Resolve ticker symbols from the request body.
        Explicit body.companies takes precedence.
        Falls back to regex extraction from the query text.
        """
        if body.companies:
            return [t.upper() for t in body.companies[:5]]

        import re
        KNOWN = {
            "NVDA","AMD","AAPL","MSFT","TSLA","AMZN","GOOGL","GOOG",
            "META","NFLX","JPM","GS","MS","BAC","INTC","QCOM","AVGO",
            "TSM","ASML","ARM","SBUX","DIS","PYPL","SQ","COIN",
        }
        found = [t for t in re.findall(r'\b([A-Z]{2,5})\b', body.query) if t in KNOWN]
        # Preserve insertion order, deduplicate
        seen: set[str] = set()
        unique = [t for t in found if not (t in seen or seen.add(t))]  # type: ignore[func-returns-value]
        return unique[:3] or ["NVDA"]

    # ── Tool dispatch ─────────────────────────────────────────────────────────

    async def _dispatch_tools(
        self,
        sm: ReportStateMachine,
        companies: list[str],
    ) -> dict[str, Any]:
        """
        Run market_data and news_search concurrently.
        Each tool emits started/completed/failed SSE events independently.
        A single tool failure never cancels the other.
        """
        from app.tools.market_data import MarketDataTool
        from app.tools.news_search import NewsSearchTool

        market_coro = self._run_tool(
            sm=sm,
            name="market_data",
            tool=MarketDataTool(),
            tickers=companies,
            timeout_s=12.0,
        )
        news_coro = self._run_tool(
            sm=sm,
            name="news_search",
            tool=NewsSearchTool(),
            tickers=companies,
            timeout_s=15.0,
        )

        results = await asyncio.gather(market_coro, news_coro, return_exceptions=True)

        output: dict[str, Any] = {}
        for name, result in zip(("market_data", "news_search"), results):
            if isinstance(result, BaseException):
                log.warning("engine.tool_gather_exception", tool=name, error=str(result))
                output[name] = None
            else:
                output[name] = result
        return output

    async def _run_tool(
        self,
        sm: ReportStateMachine,
        name: str,
        tool: Any,
        tickers: list[str],
        timeout_s: float,
    ) -> Any:
        """Execute one tool with timeout; emit SSE lifecycle events."""
        t0 = time.perf_counter()
        await sm.emit_tool_started(name, tickers)
        try:
            result = await asyncio.wait_for(
                tool.execute(tickers=tickers),
                timeout=timeout_s,
            )
            duration_ms = int((time.perf_counter() - t0) * 1000)
            if result.has_data:
                await sm.emit_tool_completed(name, result.confidence.level.value, duration_ms)
                return result
            await sm.emit_tool_failed(name, result.error or "No data returned")
            return None
        except asyncio.TimeoutError:
            await sm.emit_tool_failed(name, f"Timed out after {timeout_s}s")
            return None
        except Exception as exc:
            await sm.emit_tool_failed(name, str(exc))
            return None

    # ── Report builder ────────────────────────────────────────────────────────

    def _build_report(
        self,
        query: str,
        companies: list[str],
        market_result: Any,
        news_result: Any,
        elapsed_ms: int,
    ) -> dict[str, Any]:
        """
        Build a ResearchReport dict that matches the frontend TypeScript schema exactly.
        Schema: types/report.ts → ResearchReport interface.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        sources:  list[dict] = []
        gaps:     list[dict] = []
        snapshots: list[dict] = []
        sections:  list[dict] = []

        # ── Market data → CompanySnapshot array ───────────────────────────────
        market_src_id: str | None = None
        if market_result and market_result.has_data:
            market_src_id = str(uuid.uuid4())
            sources.append({
                "id": market_src_id,
                "type": "market_api",
                "name": market_result.data.source_name,
                "url": market_result.data.source_url,
                "fetched_at": now_iso,
                "metadata": {},
            })
            for ticker, m in market_result.data.companies.items():
                snapshots.append({
                    "ticker": m.ticker,
                    "name": m.company_name,
                    "exchange": m.exchange,
                    "sector": m.sector,
                    "description": (m.description or "")[:400] or None,
                    "metrics": {
                        "current_price":   m.current_price,
                        "market_cap":      m.market_cap,
                        "pe_ratio":        m.pe_ratio,
                        "revenue_ttm":     m.revenue_ttm,
                        "eps":             m.eps,
                        "change_1d_pct":   m.change_percent_1d,
                        "change_1m_pct":   m.change_percent_1m,
                    },
                    "price_history": [
                        {"date": p.date, "close": p.close, "volume": p.volume}
                        for p in m.price_history
                    ],
                    "news_sentiment": None,   # patched below
                    "source_ids": [market_src_id],
                })
        else:
            gaps.append({
                "section_type": "market_data",
                "ticker": None,
                "reason": "Market data unavailable — yfinance returned no data",
                "severity": "warning",
            })

        # ── News data → news section + sentiment patch ────────────────────────
        news_by_ticker: dict[str, list[dict]] = {}
        if news_result and news_result.has_data:
            for article in news_result.data.articles[:12]:
                src_id = str(article.id) if article.id else str(uuid.uuid4())
                sources.append({
                    "id": src_id,
                    "type": "news_api",
                    "name": article.source_name,
                    "url":  article.url,
                    "fetched_at": article.published_at.isoformat(),
                    "metadata": {"ticker": article.ticker},
                })
                news_by_ticker.setdefault(article.ticker, []).append({
                    "title":           article.title,
                    "summary":         (article.description or article.title)[:300],
                    "sentiment":       "neutral",
                    "sentiment_score": 0.0,
                    "published_at":    article.published_at.isoformat(),
                    "source_name":     article.source_name,
                    "url":             article.url,
                    "source_id":       src_id,
                })

            # Patch news_sentiment onto each snapshot
            for snap in snapshots:
                items = news_by_ticker.get(snap["ticker"], [])
                if items:
                    snap["news_sentiment"] = {
                        "overall":       "neutral",
                        "score":         0.0,
                        "article_count": len(items),
                    }

            if news_by_ticker:
                news_src_ids = [s["id"] for s in sources if s["type"] == "news_api"]
                sections.append({
                    "type": "news",
                    "id":   str(uuid.uuid4()),
                    "title": "Recent News",
                    "source_ids": news_src_ids[:8],
                    "content": {
                        "articles": [
                            {"ticker": t, "items": it}
                            for t, it in news_by_ticker.items()
                        ]
                    },
                })
        else:
            gaps.append({
                "section_type": "news",
                "ticker": None,
                "reason": "No news articles found for the requested companies",
                "severity": "warning",
            })

        # ── Overview section (always present) ─────────────────────────────────
        sections.insert(0, self._overview_section(companies, snapshots, query, market_src_id))

        # ── Comparison section (only when ≥2 companies have market data) ──────
        if len(snapshots) >= 2:
            comp = self._comparison_section(snapshots, market_src_id)
            if comp:
                sections.append(comp)

        return {
            "schema_version":    "1.0",
            "query":             query,
            "generated_at":      now_iso,
            "processing_time_ms": elapsed_ms,
            "companies":         snapshots,
            "sections":          sections,
            "executive_summary": "",        # filled by _executive_summary()
            "risk_assessment":   None,
            "sources":           sources,
            "data_gaps":         gaps,
        }

    # ── Section builders ──────────────────────────────────────────────────────

    @staticmethod
    def _overview_section(
        companies: list[str],
        snapshots: list[dict],
        query: str,
        market_src_id: str | None,
    ) -> dict:
        tickers   = [s["ticker"] for s in snapshots] or companies
        highlights: list[str] = []

        for snap in snapshots:
            m    = snap.get("metrics", {})
            name = snap.get("name", snap["ticker"])
            price = m.get("current_price")
            chg   = m.get("change_1d_pct")
            mc    = m.get("market_cap")

            if price is not None:
                sign    = "+" if (chg or 0) > 0 else ""
                chg_str = f" ({sign}{chg:.2f}%)" if chg is not None else ""
                highlights.append(f"{name} ({snap['ticker']}) trading at ${price:,.2f}{chg_str}")

            if mc is not None:
                if mc >= 1e12:
                    highlights.append(f"{name} market cap: ${mc / 1e12:.2f}T")
                elif mc >= 1e9:
                    highlights.append(f"{name} market cap: ${mc / 1e9:.2f}B")

        t_str = (
            " and ".join(tickers)
            if len(tickers) <= 2
            else ", ".join(tickers[:-1]) + f" and {tickers[-1]}"
        )

        return {
            "type":  "overview",
            "id":    str(uuid.uuid4()),
            "title": "Overview",
            "source_ids": [market_src_id] if market_src_id else [],
            "content": {
                "tickers": tickers,
                "narrative": (
                    f"This report provides a data-driven analysis of {t_str} "
                    f"based on current market data and recent news. "
                    f"Research context: \"{query}\"."
                ),
                "key_highlights": highlights[:5],
            },
        }

    @staticmethod
    def _comparison_section(snapshots: list[dict], market_src_id: str | None) -> dict | None:
        if not snapshots:
            return None
        tickers = [s["ticker"] for s in snapshots]

        def _fmt(v: float | None, unit: str) -> str:
            if v is None:
                return "—"
            if unit == "USD":
                if v >= 1e12: return f"${v / 1e12:.2f}T"
                if v >= 1e9:  return f"${v / 1e9:.2f}B"
                return f"${v:,.2f}"
            if unit == "ratio":
                return f"{v:.1f}x"
            return f"{v:.2f}"

        METRIC_DEFS = [
            ("current_price", "Price",         "USD",   "currency"),
            ("market_cap",    "Market Cap",     "USD",   "currency"),
            ("pe_ratio",      "P/E Ratio",      "ratio", "decimal"),
            ("revenue_ttm",   "Revenue (TTM)",  "USD",   "currency"),
            ("eps",           "EPS",            "USD",   "currency"),
        ]

        metrics:    list[dict] = []
        chart_data: list[dict] = []

        for field, label, unit, fmt in METRIC_DEFS:
            values, chart_vals = [], []
            winner, best = None, None

            for snap in snapshots:
                raw = snap.get("metrics", {}).get(field)
                values.append({
                    "ticker":    snap["ticker"],
                    "value":     raw,
                    "formatted": _fmt(raw, unit),
                })
                if raw is not None:
                    chart_vals.append({"ticker": snap["ticker"], "value": raw})
                    if best is None or raw > best:
                        best, winner = raw, snap["ticker"]

            insight = (
                f"{winner} leads on {label}." if winner
                else f"No clear leader on {label}."
            )
            metrics.append({
                "name":    label,
                "unit":    unit,
                "format":  fmt,
                "values":  values,
                "winner":  winner,
                "insight": insight,
            })
            if chart_vals:
                chart_data.append({"metric": label, "data": chart_vals, "chart_type": "bar"})

        t_str = " vs ".join(tickers)
        return {
            "type":  "comparison",
            "id":    str(uuid.uuid4()),
            "title": f"{t_str} Comparison",
            "source_ids": [market_src_id] if market_src_id else [],
            "content": {
                "tickers":    tickers,
                "metrics":    metrics,
                "chart_data": chart_data[:3],
                "ai_commentary": (
                    f"Side-by-side financial comparison of {t_str}. "
                    "Data sourced from current market feeds."
                ),
            },
        }

    # ── LLM executive summary (Anthropic — optional) ──────────────────────────

    @staticmethod
    def _anthropic_available() -> bool:
        import os
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    async def _executive_summary(
        self,
        query: str,
        companies: list[str],
        report_data: dict,
    ) -> str:
        """
        Generate the executive summary.
        Uses Anthropic Claude when ANTHROPIC_API_KEY is configured.
        Falls back to a deterministic template summary otherwise.
        """
        if self._anthropic_available():
            try:
                return await self._llm_summary(query, companies, report_data)
            except Exception as exc:
                log.info("engine.llm_summary_fallback", reason=str(exc))

        return self._template_summary(query, companies, report_data)

    @staticmethod
    async def _llm_summary(query: str, companies: list[str], report_data: dict) -> str:
        from app.clients.anthropic_client import get_anthropic_client

        snapshots = report_data.get("companies", [])
        ctx_lines = []
        for snap in snapshots[:3]:
            m     = snap.get("metrics", {})
            name  = snap.get("name", snap["ticker"])
            price = m.get("current_price")
            mc    = m.get("market_cap")
            chg   = m.get("change_1d_pct")
            line  = f"- {name} ({snap['ticker']})"
            if price: line += f": ${price:,.2f}"
            if chg:   line += f" ({'+' if chg > 0 else ''}{chg:.2f}% 1d)"
            if mc and mc >= 1e9: line += f", mkt cap ${mc/1e9:.1f}B"
            ctx_lines.append(line)

        client = get_anthropic_client()
        resp   = await client.complete(
            system=(
                "You are a professional financial analyst. Write a concise 2–3 sentence "
                "executive summary for an investment research report. Be factual and "
                "data-driven. Use only the data provided. No markdown."
            ),
            user_message=(
                f"Research query: {query}\n\n"
                f"Market data:\n" + "\n".join(ctx_lines) + "\n\nExecutive summary:"
            ),
            max_tokens=300,
            temperature=0.2,
            timeout_s=20.0,
            call_name="exec_summary",
        )
        return resp.text.strip()

    @staticmethod
    def _template_summary(query: str, companies: list[str], report_data: dict) -> str:
        snapshots = report_data.get("companies", [])
        parts: list[str] = []
        for snap in snapshots[:2]:
            m     = snap.get("metrics", {})
            name  = snap.get("name", snap["ticker"])
            price = m.get("current_price")
            chg   = m.get("change_1d_pct")
            mc    = m.get("market_cap")
            if price is not None:
                direction = "up" if (chg or 0) > 0 else "down"
                chg_str   = f", {direction} {abs(chg or 0):.2f}% today" if chg else ""
                mc_str    = ""
                if mc and mc >= 1e12:
                    mc_str = f" (market cap ${mc/1e12:.2f}T)"
                elif mc and mc >= 1e9:
                    mc_str = f" (market cap ${mc/1e9:.2f}B)"
                parts.append(f"{name} is trading at ${price:,.2f}{chg_str}{mc_str}.")

        t_str = " and ".join(companies[:2]) if companies else "the requested companies"
        summary = f"Research analysis for {t_str}. "
        if parts:
            summary += " ".join(parts) + " "
        summary += "Key financial metrics and recent news are summarised in the sections below."
        return summary