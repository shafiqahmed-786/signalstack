import { cn } from "@/lib/utils";
import { getConfidenceDisplay } from "@/features/research/utils/confidence";
import type { ConfidenceLevel } from "@/types/api";

interface ConfidenceBadgeProps {
  level: ConfidenceLevel | null;
  showLabel?: boolean;
  className?: string;
}

export function ConfidenceBadge({ level, showLabel = true, className }: ConfidenceBadgeProps) {
  const display = getConfidenceDisplay(level);

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-1.5 py-0.5 rounded text-xs font-mono",
        display.bgColor,
        display.color,
        className
      )}
      title={display.label}
    >
      <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", display.dotColor)} />
      {showLabel && display.label}
    </span>
  );
}