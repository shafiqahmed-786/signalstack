"use client";

import { CheckCircle2, XCircle, Loader2, Clock, TrendingUp, Newspaper, FileSearch, Brain } from "lucide-react";
import { cn, formatDuration } from "@/lib/utils";
import { TOOL_LABELS, PHASE_LABELS } from "../types";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import type { OrchestrationState } from "../types";
import type { ToolName } from "@/types/api";

const TOOL_ICON_MAP: Record<ToolName, React.ComponentType<{ className?: string }>> = {
  market_data: TrendingUp,
  news_search: Newspaper,
  vector_retrieval: FileSearch,
  sentiment_analysis: Brain,
};

interface OrchestrationStreamProps {
  state: OrchestrationState;
  className?: string;
}

export function OrchestrationStream({ state, className }: OrchestrationStreamProps) {
  const elapsedMs = state.startedAt
    ? (state.completedAt ?? Date.now()) - state.startedAt
    : null;

  if (state.phase === "idle") return null;

  return (
    <div className={cn("rounded-xl border border-border bg-card overflow-hidden", className)}>
      {/* Phase header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          {state.phase === "failed" ? (
            <XCircle className="w-4 h-4 text-signal-red" />
          ) : state.phase === "completed" || state.phase === "partial" ? (
            <CheckCircle2 className="w-4 h-4 text-signal-green" />
          ) : (
            <Loader2 className="w-4 h-4 text-ai animate-spin" />
          )}
          <span className="text-sm font-medium text-ink">
            {PHASE_LABELS[state.phase]}
          </span>
          {state.plan && (
            <div className="flex gap-1 ml-1">
              {state.plan.companies.map((c) => (
                <span key={c} className="px-1.5 py-0.5 rounded text-xs font-mono bg-ai-dim text-ai border border-ai/20">
                  {c}
                </span>
              ))}
            </div>
          )}
        </div>
        {elapsedMs !== null && (
          <div className="flex items-center gap-1 text-xs text-ink-muted font-mono">
            <Clock className="w-3 h-3" />
            {formatDuration(elapsedMs)}
          </div>
        )}
      </div>

      {/* Tool statuses */}
      {state.tools.length > 0 && (
        <div className="px-4 py-3 space-y-2">
          {state.tools.map((tool) => {
            const Icon = TOOL_ICON_MAP[tool.name] ?? TrendingUp;
            return (
              <div key={tool.name} className="flex items-center gap-3">
                <div className={cn(
                  "w-7 h-7 rounded-lg flex items-center justify-center shrink-0 border",
                  tool.state === "completed" ? "bg-signal-green-dim border-signal-green/20" :
                  tool.state === "failed" ? "bg-signal-red-dim border-signal-red/20" :
                  tool.state === "running" ? "bg-ai-dim border-ai/20" :
                  "bg-surface border-border"
                )}>
                  {tool.state === "running" ? (
                    <Loader2 className="w-3.5 h-3.5 text-ai animate-spin" />
                  ) : tool.state === "completed" ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-signal-green" />
                  ) : tool.state === "failed" ? (
                    <XCircle className="w-3.5 h-3.5 text-signal-red" />
                  ) : (
                    <Icon className="w-3.5 h-3.5 text-ink-muted" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <span className={cn(
                    "text-xs font-medium",
                    tool.state === "pending" ? "text-ink-muted" : "text-ink"
                  )}>
                    {TOOL_LABELS[tool.name]}
                  </span>
                  {tool.error && (
                    <span className="ml-2 text-xs text-signal-red">{tool.error}</span>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {tool.confidence && <ConfidenceBadge level={tool.confidence} showLabel={false} />}
                  {tool.duration_ms !== null && (
                    <span className="text-xs text-ink-muted font-mono">{formatDuration(tool.duration_ms)}</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Error message */}
      {state.phase === "failed" && state.error && (
        <div className="px-4 pb-3">
          <p className="text-xs text-signal-red bg-signal-red-dim rounded-lg px-3 py-2 font-mono">
            {state.error}
          </p>
        </div>
      )}
    </div>
  );
}