import type { ToolName, ConfidenceLevel, OrchestrationPhase, ToolStatus, SSEPlanPayload } from "@/types/api";

export interface OrchestrationState {
  phase: OrchestrationPhase;
  reportId: string | null;
  plan: SSEPlanPayload | null;
  tools: ToolStatus[];
  toolsSucceeded: number;
  toolsFailed: number;
  error: string | null;
  startedAt: number | null;
  completedAt: number | null;
}

export const TOOL_LABELS: Record<ToolName, string> = {
  market_data: "Market Data",
  news_search: "News Search",
  vector_retrieval: "Filing Analysis",
  sentiment_analysis: "Sentiment",
};

export const TOOL_ICONS: Record<ToolName, string> = {
  market_data: "TrendingUp",
  news_search: "Newspaper",
  vector_retrieval: "FileSearch",
  sentiment_analysis: "Brain",
};

export const PHASE_LABELS: Record<OrchestrationPhase, string> = {
  idle: "Ready",
  created: "Initializing",
  planning: "Analyzing query…",
  dispatching: "Gathering data…",
  synthesizing: "Generating report…",
  completed: "Complete",
  partial: "Complete (partial data)",
  failed: "Failed",
};

export interface QuerySuggestion {
  label: string;
  query: string;
  tickers?: string[];
}

export const QUERY_SUGGESTIONS: QuerySuggestion[] = [
  {
    label: "NVIDIA earnings analysis",
    query: "Analyse NVIDIA Q3 earnings, revenue growth, and forward guidance",
    tickers: ["NVDA"],
  },
  {
    label: "GPU market comparison",
    query: "Compare NVIDIA and AMD performance across data center and consumer GPU markets",
    tickers: ["NVDA", "AMD"],
  },
  {
    label: "Apple sentiment & news",
    query: "Summarise recent Apple news and market sentiment for Q4 2024",
    tickers: ["AAPL"],
  },
  {
    label: "Big Tech competitive analysis",
    query: "Compare Microsoft and Apple revenue, margins and AI strategy",
    tickers: ["MSFT", "AAPL"],
  },
  {
    label: "Tesla risk assessment",
    query: "Assess the key risks facing Tesla in 2025 including competition and delivery targets",
    tickers: ["TSLA"],
  },
];