import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface TickerChipProps {
  ticker: string;
  onRemove?: () => void;
  className?: string;
}

export function TickerChip({ ticker, onRemove, className }: TickerChipProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 pl-2 pr-1 py-0.5 rounded-md text-xs font-mono",
        "bg-ai-dim text-ai border border-ai/25",
        className
      )}
    >
      {ticker}
      {onRemove && (
        <button
          onClick={onRemove}
          className="ml-0.5 rounded hover:bg-ai/20 p-0.5 transition-colors"
          aria-label={`Remove ${ticker}`}
        >
          <X className="w-2.5 h-2.5" />
        </button>
      )}
    </span>
  );
}