import type { ConfidenceLevel } from "@/types/api";

export interface ConfidenceDisplay {
  label: string;
  color: string;
  bgColor: string;
  dotColor: string;
}

export function getConfidenceDisplay(level: ConfidenceLevel | null): ConfidenceDisplay {
  switch (level) {
    case "high":
      return {
        label: "High confidence",
        color: "text-signal-green",
        bgColor: "bg-signal-green-dim",
        dotColor: "bg-signal-green",
      };
    case "medium":
      return {
        label: "Medium confidence",
        color: "text-signal-amber",
        bgColor: "bg-signal-amber-dim",
        dotColor: "bg-signal-amber",
      };
    case "low":
      return {
        label: "Low confidence",
        color: "text-signal-red",
        bgColor: "bg-signal-red-dim",
        dotColor: "bg-signal-red",
      };
    default:
      return {
        label: "Unknown",
        color: "text-ink-muted",
        bgColor: "bg-surface",
        dotColor: "bg-ink-muted",
      };
  }
}

export function getSentimentDisplay(sentiment: "positive" | "negative" | "neutral") {
  switch (sentiment) {
    case "positive":
      return { label: "Positive", color: "text-signal-green", bgColor: "bg-signal-green-dim" };
    case "negative":
      return { label: "Negative", color: "text-signal-red", bgColor: "bg-signal-red-dim" };
    default:
      return { label: "Neutral", color: "text-ink-secondary", bgColor: "bg-surface" };
  }
}

export function getRiskSeverityDisplay(severity: "low" | "medium" | "high") {
  switch (severity) {
    case "high":
      return { label: "High", color: "text-signal-red", dotColor: "bg-signal-red" };
    case "medium":
      return { label: "Medium", color: "text-signal-amber", dotColor: "bg-signal-amber" };
    default:
      return { label: "Low", color: "text-signal-green", dotColor: "bg-signal-green" };
  }
}