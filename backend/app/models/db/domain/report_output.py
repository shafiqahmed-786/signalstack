"""
app/models/domain/report_output.py

The ResearchReport structured output contract.

This is the authoritative JSON schema that:
  1. The Synthesizer is instructed to produce (injected into the system prompt)
  2. The Synthesizer's raw output is validated against (Pydantic.model_validate_json)
  3. Stored verbatim as JSONB in research_reports.report_data
  4. Served to the frontend which renders each section.type to a React component

DESIGN RULE: Do not change field names without updating:
  - synthesizer_v1.py (the JSON schema in the system prompt)
  - The frontend TypeScript interfaces in lib/types/report.ts
  - The schema_version field (bump to "1.1" etc.)
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator

# ── Shared primitives ──────────────────────────────────────────────────────────


class PricePoint(BaseModel):
    """Single OHLC data point for chart rendering."""

    date: str = Field(description="ISO date string YYYY-MM-DD")
    close: float
    volume: int


class SourceAttribution(BaseModel):
    """
    Citation registry entry. Every claim in the report references an id
    from the root ResearchReport.sources list.
    """

    id: str = Field(description="UUID string — referenced throughout the report as source_id")
    type: Literal["market_api", "news_api", "vector_db", "filing"]
    name: str = Field(description='Human-readable name e.g. "Yahoo Finance", "Reuters"')
    url: str | None = None
    fetched_at: str = Field(description="ISO 8601 datetime string")
    metadata: dict = Field(
        default_factory=dict,
        description="Arbitrary context: ticker, article_id, chunk_id, doc_title, etc.",
    )


class DataGap(BaseModel):
    """
    Transparency record for data the system could not retrieve.
    Rendered as warnings in the UI; never silently omitted.
    """

    section_type: str
    ticker: str | None = None
    reason: str = Field(description='e.g. "Market data API rate limited"')
    severity: Literal["warning", "error"] = Field(
        description="warning=partial data present, error=section entirely omitted"
    )


# ── Company snapshot ───────────────────────────────────────────────────────────


class CompanyMetricsSummary(BaseModel):
    """Key financial metrics for a single company."""

    current_price: float | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    revenue_ttm: float | None = None
    eps: float | None = None
    change_1d_pct: float | None = None
    change_1m_pct: float | None = None


class NewsSentimentSummary(BaseModel):
    overall: Literal["positive", "negative", "neutral"]
    score: float = Field(ge=-1.0, le=1.0)
    article_count: int = Field(ge=0)


class CompanySnapshot(BaseModel):
    """
    One entry per ticker in the report. Contains all company-level
    data the frontend needs to render CompanyCard and PriceChart.
    """

    ticker: str
    name: str
    exchange: str | None = None
    sector: str | None = None
    description: str | None = Field(
        None, description="Short company description from market data API"
    )
    metrics: CompanyMetricsSummary
    price_history: list[PricePoint] = Field(
        default_factory=list,
        description="30-day daily close prices for chart rendering",
    )
    news_sentiment: NewsSentimentSummary | None = None
    source_ids: list[str] = Field(
        default_factory=list,
        description="IDs from the root sources registry that provided this data",
    )


# ── Report sections (discriminated union by `type`) ────────────────────────────


class BaseSection(BaseModel):
    """Common fields for every report section."""

    id: str = Field(description="Unique section identifier within this report")
    title: str
    source_ids: list[str] = Field(
        default_factory=list,
        description="Source IDs that back the claims in this section",
    )


class OverviewSectionContent(BaseModel):
    tickers: list[str]
    narrative: str = Field(description="2–3 paragraph AI-written analysis")
    key_highlights: list[str] = Field(
        description="Bullet points, max 5 items",
        max_length=5,
    )


class OverviewSection(BaseSection):
    """General company summary — always generated."""

    type: Literal["overview"]
    content: OverviewSectionContent


class ComparisonMetricValue(BaseModel):
    ticker: str
    value: float | None
    formatted: str = Field(description='Pre-formatted display string e.g. "$2.15T"')


class ComparisonMetric(BaseModel):
    name: str = Field(description='e.g. "Revenue (TTM)", "P/E Ratio"')
    unit: Literal["USD", "percent", "ratio", "number"]
    format: Literal["currency", "percentage", "decimal", "integer"]
    values: list[ComparisonMetricValue]
    winner: str | None = Field(
        None, description="Ticker of the best-performing company on this metric"
    )
    insight: str = Field(description="One-sentence AI observation about this metric")


class ComparisonChartDataset(BaseModel):
    metric: str
    data: list[dict] = Field(
        description='[{"ticker": "NVDA", "value": 22.1}, ...]'
    )
    chart_type: Literal["bar", "line"]


class ComparisonSectionContent(BaseModel):
    tickers: list[str]
    metrics: list[ComparisonMetric]
    chart_data: list[ComparisonChartDataset]
    ai_commentary: str = Field(description="Overall comparative analysis paragraph")


class ComparisonSection(BaseSection):
    """Side-by-side metric comparison table + bar chart."""

    type: Literal["comparison"]
    content: ComparisonSectionContent


class EarningsHighlights(BaseModel):
    revenue: dict | None = Field(
        None,
        description='{"actual": 22100000000, "yoy_growth_pct": 14.2}',
    )
    eps: dict | None = Field(
        None,
        description='{"actual": 5.16, "beat_miss": "beat"}',
    )
    guidance: str | None = Field(None, description="Forward guidance excerpt or summary")


class FilingExcerpt(BaseModel):
    text: str = Field(description="Verbatim chunk from the source document")
    document_title: str
    document_type: str = Field(description='"10-K" | "earnings_transcript" | "analyst_report"')
    relevance_score: float = Field(ge=0.0, le=1.0)
    source_id: str


class EarningsSectionContent(BaseModel):
    ticker: str
    period: str = Field(description='e.g. "Q3 FY2024"')
    highlights: EarningsHighlights
    narrative: str
    filing_excerpts: list[FilingExcerpt] = Field(default_factory=list)


class EarningsSection(BaseSection):
    """Earnings analysis with filing excerpts."""

    type: Literal["earnings"]
    content: EarningsSectionContent


class NewsItem(BaseModel):
    title: str
    summary: str = Field(description="AI-compressed to 2 sentences")
    sentiment: Literal["positive", "negative", "neutral"]
    sentiment_score: float = Field(ge=-1.0, le=1.0)
    published_at: str = Field(description="ISO 8601 datetime string")
    source_name: str
    url: str
    source_id: str


class TickerNewsGroup(BaseModel):
    ticker: str
    items: list[NewsItem]


class NewsSectionContent(BaseModel):
    articles: list[TickerNewsGroup]


class NewsSection(BaseSection):
    """Recent news with per-article sentiment classification."""

    type: Literal["news"]
    content: NewsSectionContent


class FilingInsightsSectionContent(BaseModel):
    query_used: str = Field(description="The semantic search query sent to ChromaDB")
    results: list[FilingExcerpt]


class FilingInsightsSection(BaseSection):
    """Vector retrieval results rendered as quoted document excerpts."""

    type: Literal["filing_insights"]
    content: FilingInsightsSectionContent


class RiskFactor(BaseModel):
    category: Literal["market", "competitive", "regulatory", "operational", "macro"]
    title: str
    description: str
    severity: Literal["low", "medium", "high"]
    source_id: str | None = None


class RiskAssessment(BaseModel):
    overall_level: Literal["low", "medium", "high"]
    factors: list[RiskFactor]
    summary: str


class RiskSection(BaseSection):
    """Structured risk assessment — generated when query mentions risk or broad analysis."""

    type: Literal["risk"]
    content: RiskAssessment


# Discriminated union — frontend switches on `type` to render the correct component
ReportSection = Annotated[
    Union[
        OverviewSection,
        ComparisonSection,
        EarningsSection,
        NewsSection,
        FilingInsightsSection,
        RiskSection,
    ],
    Field(discriminator="type"),
]


# ── Root report object ─────────────────────────────────────────────────────────


class ResearchReport(BaseModel):
    """
    Root structured output object.

    Stored verbatim as JSONB in research_reports.report_data.
    The schema_version field allows the frontend and migration scripts
    to handle multiple versions gracefully.
    """

    schema_version: Literal["1.0"] = "1.0"
    query: str
    generated_at: str = Field(description="ISO 8601 UTC datetime")
    processing_time_ms: int = Field(ge=0)

    # Per-company data (one entry per resolved ticker)
    companies: list[CompanySnapshot]

    # Ordered sections — frontend renders each section.type to a React component
    sections: list[ReportSection]

    # Executive summary — always present, first thing the reader sees
    executive_summary: str

    # Risk assessment if the query warranted it
    risk_assessment: RiskAssessment | None = None

    # Citation registry — all source_ids throughout the report map here
    sources: list[SourceAttribution]

    # Transparency: what the system couldn't retrieve
    data_gaps: list[DataGap] = Field(default_factory=list)

    @field_validator("companies")
    @classmethod
    def companies_not_empty(cls, v: list[CompanySnapshot]) -> list[CompanySnapshot]:
        if not v:
            raise ValueError("ResearchReport must contain at least one CompanySnapshot")
        return v

    @field_validator("sections")
    @classmethod
    def sections_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError(
                "ResearchReport must contain at least one section. "
                "If synthesis failed entirely, the orchestrator should surface an error "
                "rather than returning an empty report."
            )
        return v

    @model_validator(mode="after")
    def validate_source_id_integrity(self) -> "ResearchReport":
        """
        Verify every source_id referenced in sections and company snapshots
        exists in the root sources registry.

        This runs at validation time so corrupt reports are never persisted.
        """
        registered_ids = {s.id for s in self.sources}

        # Check company snapshots
        for company in self.companies:
            for sid in company.source_ids:
                if sid not in registered_ids:
                    raise ValueError(
                        f"Company {company.ticker} references unknown source_id={sid!r}. "
                        f"All source IDs must be registered in ResearchReport.sources."
                    )

        # Check sections
        for section in self.sections:
            for sid in section.source_ids:
                if sid not in registered_ids:
                    raise ValueError(
                        f"Section {section.id!r} references unknown source_id={sid!r}."
                    )

        return self

    def to_json_schema_str(self) -> str:
        """
        Returns the JSON schema as a string for injection into the
        synthesizer system prompt.
        """
        import json

        return json.dumps(self.model_json_schema(), indent=2)

    @classmethod
    def from_json(cls, raw_json: str) -> "ResearchReport":
        """
        Deserialise from a raw JSON string, stripping accidental markdown fences.
        Raises ValidationError on schema violations.
        """
        import re

        # Strip ```json ... ``` fences that LLMs sometimes add despite instructions
        clean = re.sub(r"^```(?:json)?\s*", "", raw_json.strip(), flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean)
        return cls.model_validate_json(clean)