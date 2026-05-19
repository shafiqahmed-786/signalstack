"""Domain models for research reports and status."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class ReportStatus(str, Enum):
    """Status enum for research reports throughout their lifecycle."""

    CREATED = "created"
    PLANNING = "planning"
    DISPATCHING = "dispatching"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        """Check if status is a terminal state (no further transitions possible)."""
        return self in (
            ReportStatus.COMPLETED,
            ReportStatus.PARTIAL,
            ReportStatus.FAILED,
            ReportStatus.CANCELLED,
        )


class ResearchReport(BaseModel):
    """Research report output from AI synthesis."""

    schema_version: str = "1.0"
    query: str
    generated_at: str  # ISO 8601 timestamp
    processing_time_ms: int
    companies: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    executive_summary: str = ""
    risk_assessment: dict[str, Any] | None = None
    sources: list[dict[str, Any]] = []
    data_gaps: list[dict[str, Any]] = []

    class Config:
        """Pydantic model config."""

        arbitrary_types_allowed = True
