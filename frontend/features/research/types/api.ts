// API layer types: responses, errors, SSE events

import type { ResearchReport } from "./report";

// ── Standard response envelope ────────────────────────────────────────────────

export interface ApiSuccess<T> {
  data: T;
  meta: { request_id: string; timestamp: string };
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: { field: string; message: string; type: string }[];
  };
}

// ── Report DTOs (matching backend response schemas) ───────────────────────────

export type ReportStatus =
  | "created"
  | "planning"
  | "dispatching"
  | "synthesizing"
  | "completed"
  | "partial"
  | "failed"
  | "cancelled";

export interface ReportSummary {
  id: string;
  query: string;
  title: string | null;
  status: ReportStatus;
  companies: string[];
  tags: string[];
  is_pinned: boolean;
  processing_time_ms: number | null;
  created_at: string;
  cache_hit: boolean;
}

export interface ReportDetail extends ReportSummary {
  report: ResearchReport | null;
  error_message: string | null;
}

export interface ReportListResponse {
  reports: ReportSummary[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface ReportUpdatePayload {
  title?: string;
  tags?: string[];
  is_pinned?: boolean;
}

// ── SSE event payloads (matching ReportStateMachine emissions) ────────────────

export type OrchestrationPhase =
  | "idle"
  | "created"
  | "planning"
  | "dispatching"
  | "synthesizing"
  | "completed"
  | "partial"
  | "failed";

export type ToolName = "market_data" | "news_search" | "vector_retrieval" | "sentiment_analysis";
export type ConfidenceLevel = "high" | "medium" | "low";

export interface SSEPlanPayload {
  companies: string[];
  intent: string;
  tools: ToolName[];
}

export interface SSEToolStartedPayload {
  tool: ToolName;
  tickers: string[];
}

export interface SSEToolCompletedPayload {
  tool: ToolName;
  confidence: ConfidenceLevel;
  duration_ms: number;
}

export interface SSEToolFailedPayload {
  tool: ToolName;
  error: string;
  will_retry: boolean;
}

export interface SSEReportEventPayload {
  report_id: string;
  status: ReportStatus;
  plan?: SSEPlanPayload;
  tools_succeeded?: number;
  tools_failed?: number;
  processing_time_ms?: number;
  report?: ResearchReport;
  error?: string;
}

export interface SSEEvent {
  event: string;
  data: SSEReportEventPayload | SSEToolStartedPayload | SSEToolCompletedPayload | SSEToolFailedPayload;
}

export interface ToolStatus {
  name: ToolName;
  state: "pending" | "running" | "completed" | "failed";
  confidence: ConfidenceLevel | null;
  duration_ms: number | null;
  error: string | null;
}