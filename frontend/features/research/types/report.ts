// Mirror of backend ResearchReport JSON contract (app/models/domain/report_output.py)

export interface PricePoint {
  date: string;
  close: number;
  volume: number;
}

export interface SourceAttribution {
  id: string;
  type: "market_api" | "news_api" | "vector_db" | "filing";
  name: string;
  url: string | null;
  fetched_at: string;
  metadata: Record<string, unknown>;
}

export interface DataGap {
  section_type: string;
  ticker: string | null;
  reason: string;
  severity: "warning" | "error";
}

export interface CompanyMetrics {
  current_price: number | null;
  market_cap: number | null;
  pe_ratio: number | null;
  revenue_ttm: number | null;
  eps: number | null;
  change_1d_pct: number | null;
  change_1m_pct: number | null;
}

export interface NewsSentiment {
  overall: "positive" | "negative" | "neutral";
  score: number;
  article_count: number;
}

export interface CompanySnapshot {
  ticker: string;
  name: string;
  exchange: string | null;
  sector: string | null;
  description: string | null;
  metrics: CompanyMetrics;
  price_history: PricePoint[];
  news_sentiment: NewsSentiment | null;
  source_ids: string[];
}

export interface OverviewSection {
  type: "overview";
  id: string;
  title: string;
  source_ids: string[];
  content: {
    tickers: string[];
    narrative: string;
    key_highlights: string[];
  };
}

export interface ComparisonMetricValue {
  ticker: string;
  value: number | null;
  formatted: string;
}

export interface ComparisonMetric {
  name: string;
  unit: string;
  format: string;
  values: ComparisonMetricValue[];
  winner: string | null;
  insight: string;
}

export interface ComparisonSection {
  type: "comparison";
  id: string;
  title: string;
  source_ids: string[];
  content: {
    tickers: string[];
    metrics: ComparisonMetric[];
    chart_data: { metric: string; data: { ticker: string; value: number }[]; chart_type: string }[];
    ai_commentary: string;
  };
}

export interface FilingExcerpt {
  text: string;
  document_title: string;
  document_type: string;
  relevance_score: number;
  source_id: string;
}

export interface EarningsSection {
  type: "earnings";
  id: string;
  title: string;
  source_ids: string[];
  content: {
    ticker: string;
    period: string;
    highlights: {
      revenue: { actual: number; yoy_growth_pct: number } | null;
      eps: { actual: number; beat_miss: "beat" | "miss" | "in_line" | null } | null;
      guidance: string | null;
    };
    narrative: string;
    filing_excerpts: FilingExcerpt[];
  };
}

export interface NewsItem {
  title: string;
  summary: string;
  sentiment: "positive" | "negative" | "neutral";
  sentiment_score: number;
  published_at: string;
  source_name: string;
  url: string;
  source_id: string;
}

export interface NewsSection {
  type: "news";
  id: string;
  title: string;
  source_ids: string[];
  content: {
    articles: { ticker: string; items: NewsItem[] }[];
  };
}

export interface RiskFactor {
  category: "market" | "competitive" | "regulatory" | "operational" | "macro";
  title: string;
  description: string;
  severity: "low" | "medium" | "high";
  source_id: string | null;
}

export interface RiskSection {
  type: "risk";
  id: string;
  title: string;
  source_ids: string[];
  content: {
    overall_level: "low" | "medium" | "high";
    factors: RiskFactor[];
    summary: string;
  };
}

export interface FilingInsightsSection {
  type: "filing_insights";
  id: string;
  title: string;
  source_ids: string[];
  content: {
    query_used: string;
    results: FilingExcerpt[];
  };
}

export type ReportSection =
  | OverviewSection
  | ComparisonSection
  | EarningsSection
  | NewsSection
  | RiskSection
  | FilingInsightsSection;

export interface ResearchReport {
  schema_version: "1.0";
  query: string;
  generated_at: string;
  processing_time_ms: number;
  companies: CompanySnapshot[];
  sections: ReportSection[];
  executive_summary: string;
  risk_assessment: RiskSection["content"] | null;
  sources: SourceAttribution[];
  data_gaps: DataGap[];
}