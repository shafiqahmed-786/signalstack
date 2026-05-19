"use client";

import {
  TrendingUp, Newspaper, FileSearch, Brain,
  Loader2, CheckCircle2, XCircle, Clock,
} from "lucide-react";
import { cn, formatDuration } from "@/lib/utils";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import { TOOL_LABELS } from "@/features/research/types";
import type { ToolStatus, ToolName } from "@/types/api";

const ICONS: Record<ToolName, React.ComponentType<{ className?: string }>> = {
  market_data:       TrendingUp,
  news_search:       Newspaper,
  vector_retrieval:  FileSearch,
  sentiment_analysis: Brain,
};

function ToolCard({ tool }: { tool: ToolStatus }) {
  const Icon = ICONS[tool.name] ?? TrendingUp;

  const cardBorder =
    tool.state === "completed" ? "border-signal-green/25 hover:border-signal-green/40" :
    tool.state === "failed"    ? "border-signal-red/25 hover:border-signal-red/40"     :
    tool.state === "running"   ? "border-ai/30"                                        :
                                 "border-border";

  const iconStyle =
    tool.state === "completed" ? "bg-signal-green-dim text-signal-green" :
    tool.state === "failed"    ? "bg-signal-red-dim text-signal-red"     :
    tool.state === "running"   ? "bg-ai-dim text-ai"                     :
                                 "bg-surface text-ink-muted";

  return (
    <div
      className={cn("p-3 rounded-xl border bg-card transition-colors space-y-2.5", cardBorder)}
      role="status"
      aria-label={`${TOOL_LABELS[tool.name]}: ${tool.state}`}
    >
      <div className="flex items-center justify-between">
        <div className={cn("w-7 h-7 rounded-lg flex items-center justify-center", iconStyle)}>
          {tool.state === "running"
            ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
            : <Icon className="w-3.5 h-3.5" />
          }
        </div>
        <span aria-hidden="true">
          {tool.state === "completed" && <CheckCircle2 className="w-3.5 h-3.5 text-signal-green" />}
          {tool.state === "failed"    && <XCircle      className="w-3.5 h-3.5 text-signal-red"   />}
        </span>
      </div>

      <div>
        <p className="text-xs font-medium text-ink">{TOOL_LABELS[tool.name]}</p>
        {tool.error && (
          <p className="text-xs text-signal-red font-mono mt-0.5 line-clamp-2">{tool.error}</p>
        )}
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        {tool.confidence && (
          <ConfidenceBadge level={tool.confidence} showLabel={false} />
        )}
        {tool.duration_ms !== null && (
          <span className="flex items-center gap-0.5 text-xs text-ink-muted font-mono">
            <Clock className="w-2.5 h-2.5" aria-hidden="true" />
            {formatDuration(tool.duration_ms)}
          </span>
        )}
        {tool.state === "pending" && (
          <span className="text-xs text-ink-muted font-mono">Queued</span>
        )}
      </div>
    </div>
  );
}

interface ToolExecutionGridProps {
  tools: ToolStatus[];
  className?: string;
}

export function ToolExecutionGrid({ tools, className }: ToolExecutionGridProps) {
  if (!tools.length) return null;

  return (
    <div
      className={cn("grid grid-cols-2 sm:grid-cols-4 gap-2", className)}
      aria-label="Tool execution status"
    >
      {tools.map((tool) => (
        <ToolCard key={tool.name} tool={tool} />
      ))}
    </div>
  );
}