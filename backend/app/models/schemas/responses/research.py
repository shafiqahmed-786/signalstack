"""
Research API Schemas — Request and Response DTOs
=================================================
These are the API-facing Pydantic models for the research endpoints.

Layering:
  HTTP Request → ResearchQueryRequest (validates/sanitizes input)
  Service layer → domain models (ResearchReport, ResearchPlan, etc.)
  API Response  → ResearchReportResponse, ReportListResponse, etc.

ResearchQueryRequest applies security sanitization (length limits,
character filtering, ticker format validation) before the input
ever reaches the orchestration layer.
"""
from __future__ import annotations

import re
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.domain.research import ResearchReport


# ── Security constants ──────────────────────────────────────────────────────────

_QUERY_MIN_LENGTH = 10
_QUERY_MAX_LENGTH = 500
_MAX_COMPANIES_IN_REQUEST = 5
_TICKER_PATTERN = re.compile(r"^[A-Z]{1,5}$")

# Characters disallowed in research queries (prompt injection vectors)
_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize_query(raw: str) -> str:
    """
    Sanitize a research query string:
      1. NFKC unicode normalization (prevents homoglyph attacks)
      2. Strip HTML tags (bleach not required — regex sufficient for our threat model)
      3. Remove control characters
      4. Collapse whitespace
      5. Hard length cap
    """
    # 1. Unicode normalization
    text = unicodedata.normalize("NFKC", raw)
    # 2. Strip anything that looks like an HTML tag
    text = re.sub(r"<[^>]*>", " ", text)
    # 3. Remove control characters
    text = _CONTROL_CHAR_PATTERN.sub("", text)
    # 4. Collapse whitespace
    text = " ".join(text.split())
    # 5. Hard cap
    return text[:_QUERY_MAX_LENGTH]


def _sanitize_ticker(raw: str) -> str:
    """Normalize and validate a ticker symbol."""
    cleaned = re.sub(r"[^A-Za-z]", "", raw).upper().strip()
    if not _TICKER_PATTERN.match(cleaned):
        raise ValueError(
            f"'{raw}' is not a valid ticker symbol. "
            "Tickers must be 1–5 uppercase letters (e.g., NVDA, AAPL)."
        )
    return cleaned


# ── Request DTOs ────────────────────────────────────────────────────────────────

class ResearchQueryRequest(BaseModel):
    """
    Validated and sanitized request body for POST /api/v1/research.

    Security invariants guaranteed after validation:
      - query is stripped of HTML, control chars, and unicode tricks
      - companies are uppercase alphanumeric ticker symbols only
      - No duplicate companies
      - Length limits enforced before the string ever reaches the LLM
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(
        ...,
        min_length=_QUERY_MIN_LENGTH,
        max_length=_QUERY_MAX_LENGTH,
        description="Natural language research query (10–500 characters).",
    )
    # Optional ticker hints — the planner will also extract companies from the query text
    companies: list[str] | None = Field(
        default=None,
        max_length=_MAX_COMPANIES_IN_REQUEST,
        description=(
            "Optional list of ticker symbols to include. "
            "The planner will also extract companies from the query text."
        ),
    )

    @field_validator("query", mode="before")
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        sanitized = _sanitize_query(str(v))
        if len(sanitized) < _QUERY_MIN_LENGTH:
            raise ValueError(
                f"Query must be at least {_QUERY_MIN_LENGTH} characters after sanitization."
            )
        return sanitized

    @field_validator("companies", mode="before")
    @classmethod
    def sanitize_companies(cls, v: object) -> list[str] | None:
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("companies must be a list of ticker strings")
        return [_sanitize_ticker(ticker) for ticker in v]

    @model_validator(mode="after")
    def no_duplicate_tickers(self) -> "ResearchQueryRequest":
        if self.companies and len(self.companies) != len(set(self.companies)):
            raise ValueError("Duplicate ticker symbols in companies list")
        return self


class ReportUpdateRequest(BaseModel):
    """Request body for PATCH /api/v1/research/{id}."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = Field(default=None, max_length=10)
    is_pinned: bool | None = None

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v: object) -> list[str] | None:
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("tags must be a list of strings")
        normalized = []
        for tag in v:
            tag_clean = str(tag).lower().strip()[:50]
            if tag_clean:
                normalized.append(tag_clean)
        if len(normalized) != len(set(normalized)):
            raise ValueError("Duplicate tags are not allowed")
        return normalized


# ── Response DTOs ────────────────────────────────────────────────────────────────

class ReportStatusResponse(BaseModel):
    """Lightweight status response for polling GET /research/{id}/status."""

    model_config = ConfigDict(frozen=True)

    report_id: str
    status: str
    query: str
    companies: list[str]
    created_at: str
    updated_at: str
    error_message: str | None = None


class ReportListItemResponse(BaseModel):
    """Compact representation for the report list view. No full report_data."""

    model_config = ConfigDict(frozen=True)

    id: str
    query: str
    title: str | None
    status: str
    companies: list[str]
    tags: list[str]
    is_pinned: bool
    is_archived: bool
    cache_hit: bool
    processing_time_ms: int | None
    created_at: str
    updated_at: str


class ResearchReportResponse(BaseModel):
    """
    Full research report response for GET /research/{id}.

    'report' is None when status is not COMPLETED or PARTIAL_SUCCESS.
    The frontend checks 'status' first before rendering 'report'.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    query: str
    title: str | None
    status: str
    companies: list[str]
    tags: list[str]
    is_pinned: bool
    is_archived: bool

    # The full structured report — None while processing
    report: ResearchReport | None = None

    # Partial failure info
    error_message: str | None = None
    cache_hit: bool

    # Timing
    processing_time_ms: int | None = None
    total_tokens_used: int | None = None
    model_used: str | None = None
    tools_called: list[str]

    created_at: str
    updated_at: str


class ReportListResponse(BaseModel):
    """Paginated list of report summaries."""

    model_config = ConfigDict(frozen=True)

    items: list[ReportListItemResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class ResearchQueryAcceptedResponse(BaseModel):
    """
    Immediate response to POST /research when the orchestration runs async.
    The client uses 'report_id' to poll status or connect to the SSE stream.
    """

    model_config = ConfigDict(frozen=True)

    report_id: str
    status: str = "queued"
    stream_url: str        # e.g. "/api/v1/research/{id}/stream"
    poll_url: str          # e.g. "/api/v1/research/{id}/status"
    message: str = "Research query accepted. Use stream_url for real-time updates."


# ── Generic API envelope ────────────────────────────────────────────────────────

class ApiMeta(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str | None = None
    timestamp: str


class StandardResponse[T](BaseModel):
    """
    Standard API response envelope.

    Usage:
        return StandardResponse(data=UserMeResponse(...), meta=ApiMeta(...))
    """

    data: T
    meta: ApiMeta | None = None