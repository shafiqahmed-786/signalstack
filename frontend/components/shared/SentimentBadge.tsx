import { cn } from "@/lib/utils";
import { getSentimentDisplay } from "@/features/research/utils/confidence";

interface SentimentBadgeProps {
  sentiment: "positive" | "negative" | "neutral";
  score?: number;
  className?: string;
}

export function SentimentBadge({ sentiment, score, className }: SentimentBadgeProps) {
  const display = getSentimentDisplay(sentiment);

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-mono border border-white/5",
        display.bgColor,
        display.color,
        className
      )}
    >
      {sentiment === "positive" ? "↑" : sentiment === "negative" ? "↓" : "→"}
      {display.label}
      {score !== undefined && (
        <span className="opacity-60 ml-0.5">({score > 0 ? "+" : ""}{score.toFixed(2)})</span>
      )}
    </span>
  );
}