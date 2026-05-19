import { cn } from "@/lib/utils";
import type { ReportStatus } from "@/types/api";

interface StatusBadgeProps {
  status: ReportStatus;
  className?: string;
}

const STATUS_CONFIG: Record<ReportStatus, { label: string; classes: string; pulse?: boolean }> = {
  created:      { label: "Created",     classes: "text-ink-muted bg-surface border-border" },
  planning:     { label: "Planning",    classes: "text-signal-blue bg-signal-blue-dim border-signal-blue/30", pulse: true },
  dispatching:  { label: "Gathering",   classes: "text-signal-blue bg-signal-blue-dim border-signal-blue/30", pulse: true },
  synthesizing: { label: "Synthesizing",classes: "text-ai bg-ai-dim border-ai/30", pulse: true },
  completed:    { label: "Completed",   classes: "text-signal-green bg-signal-green-dim border-signal-green/30" },
  partial:      { label: "Partial",     classes: "text-signal-amber bg-signal-amber-dim border-signal-amber/30" },
  failed:       { label: "Failed",      classes: "text-signal-red bg-signal-red-dim border-signal-red/30" },
  cancelled:    { label: "Cancelled",   classes: "text-ink-muted bg-surface border-border" },
};

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.created;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-mono border",
        config.classes,
        className
      )}
    >
      <span
        className={cn(
          "w-1.5 h-1.5 rounded-full",
          config.classes.includes("text-ai") ? "bg-ai" :
          config.classes.includes("text-signal-green") ? "bg-signal-green" :
          config.classes.includes("text-signal-red") ? "bg-signal-red" :
          config.classes.includes("text-signal-amber") ? "bg-signal-amber" :
          config.classes.includes("text-signal-blue") ? "bg-signal-blue" : "bg-ink-muted",
          config.pulse && "animate-pulse-ai"
        )}
      />
      {config.label}
    </span>
  );
}