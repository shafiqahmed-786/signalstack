import { formatCurrency, formatPercent, formatNumber } from "@/lib/utils";

/** Format a metric value using the backend-specified format string. */
export function formatMetricValue(
  value: number | null,
  format: string
): string {
  if (value === null || value === undefined) return "—";
  switch (format) {
    case "currency":
      return formatCurrency(value, true);
    case "percentage":
      return formatPercent(value, false);
    case "decimal":
      return formatNumber(value);
    case "integer":
      return Math.round(value).toLocaleString("en-US");
    default:
      return String(value);
  }
}

/** Map earnings beat/miss to a display label and color class. */
export function formatEarningsBeat(
  beatMiss: "beat" | "miss" | "in_line" | null
): { label: string; color: string } {
  switch (beatMiss) {
    case "beat":
      return { label: "Beat estimates", color: "text-signal-green" };
    case "miss":
      return { label: "Missed estimates", color: "text-signal-red" };
    case "in_line":
      return { label: "In line with estimates", color: "text-ink-secondary" };
    default:
      return { label: "—", color: "text-ink-muted" };
  }
}

/** Format a year-over-year growth percentage with sign. */
export function formatYoYGrowth(pct: number): string {
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}% YoY`;
}

/** Format a relevance score from ChromaDB (0–1) as a readable percentage. */
export function formatRelevanceScore(score: number): string {
  return `${(score * 100).toFixed(0)}% match`;
}

/** Format a sentiment score (-1 to 1) as a signed percentage string. */
export function formatSentimentScore(score: number): string {
  if (Math.abs(score) < 0.05) return "Neutral";
  const sign = score > 0 ? "+" : "";
  return `${sign}${(score * 100).toFixed(0)}%`;
}

/** Produce a human-readable risk category label. */
export function formatRiskCategory(
  category: "market" | "competitive" | "regulatory" | "operational" | "macro"
): string {
  return category.charAt(0).toUpperCase() + category.slice(1);
}