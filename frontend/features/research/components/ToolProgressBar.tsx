import {
  CheckCircle2,
  XCircle,
  Loader2,
  TrendingUp,
  Newspaper,
  FileSearch,
  Brain,
} from "lucide-react";
import { cn, formatDuration } from "@/lib/utils";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import { TOOL_LABELS } from "../types";
import type { ToolStatus, ToolName } from "@/types/api";

const TOOL_ICONS: Record<ToolName, React.ComponentType<{ className?: string }>> = {
  market_data: TrendingUp,
  news_search: Newspaper,
  vector_retrieval: FileSearch,
  sentiment_analysis: Brain,
};

interface ToolProgressBarProps {
  tools: ToolStatus[];
  /** Reduce padding and icon size for compact layout contexts */
  compact?: boolean;
  className?: string;
}

function ToolRow({ tool, compact }: { tool: ToolStatus; compact: boolean }) {
  const Icon = TOOL_ICONS[tool.name] ?? TrendingUp;
  const iconSize = compact ? "w-3 h-3" : "w-3.5 h-3.5";

  const stateColor =
    tool.state === "completed" ? "text-signal-green" :
    tool.state === "failed"    ? "text-signal-red" :
    tool.state === "running"   ? "text-ai" :
                                 "text-ink-muted";

  return (
    <div className={cn("flex items-center gap-2.5", compact ? "py-0.5" : "py-1.5")}>
      <span className={cn("shrink-0", stateColor)}>
        {tool.state === "running" ? (
          <Loader2 className={cn(iconSize, "animate-spin")} />
        ) : tool.state === "completed" ? (
          <CheckCircle2 className={iconSize} />
        ) : tool.state === "failed" ? (
          <XCircle className={iconSize} />
        ) : (
          <Icon className={iconSize} />
        )}
      </span>

      <span className={cn(
        "flex-1 min-w-0 text-xs truncate",
        tool.state === "pending" ? "text-ink-muted" : "text-ink"
      )}>
        {TOOL_LABELS[tool.name]}
        {tool.error && (
          <span className="ml-1.5 text-signal-red font-mono">{tool.error}</span>
        )}
      </span>

      <div className="flex items-center gap-1.5 shrink-0">
        {tool.confidence && (
          <ConfidenceBadge level={tool.confidence} showLabel={false} />
        )}
        {!compact && tool.duration_ms !== null && (
          <span className="text-xs text-ink-muted font-mono">
            {formatDuration(tool.duration_ms)}
          </span>
        )}
      </div>
    </div>
  );
}

export function ToolProgressBar({ tools, compact = false, className }: ToolProgressBarProps) {
  if (!tools.length) return null;

  return (
    <div className={cn("space-y-0.5", !compact && "px-4 py-3", className)}>
      {tools.map((tool) => (
        <ToolRow key={tool.name} tool={tool} compact={compact} />
      ))}
    </div>
  );
}