"use client";

import { CheckCircle2, XCircle, Search, Cpu, Zap } from "lucide-react";
import { cn, formatDuration } from "@/lib/utils";
import { deriveTimeline } from "@/features/research/utils/timeline";
import { TOOL_LABELS } from "@/features/research/types";
import { ConfidenceBadge } from "@/components/shared/ConfidenceBadge";
import type { OrchestrationState } from "@/features/research/types";
import type { TimelineEvent } from "@/features/research/utils/timeline";
import type { ConfidenceLevel, ToolName } from "@/types/api";

const PHASE_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  planning: Search,
  synthesizing: Cpu,
};

function NodeIcon({ event }: { event: TimelineEvent }) {
  const size = "w-2.5 h-2.5";

  if (event.isError) return <XCircle className={size} />;
  if (event.kind === "tool_completed") return <CheckCircle2 className={size} />;

  if (event.kind === "phase_start" || event.kind === "phase_complete") {
    const Icon = (event.phase ? PHASE_ICONS[event.phase] : null) ?? Zap;
    return <Icon className={size} />;
  }

  return <span className="w-1.5 h-1.5 rounded-full bg-current" />;
}

function TimelineRow({ event, isLast }: { event: TimelineEvent; isLast: boolean }) {
  const isPhase = event.kind === "phase_start" || event.kind === "phase_complete";

  const nodeColor = event.isError
    ? "border-signal-red text-signal-red bg-signal-red-dim"
    : event.kind === "tool_completed"
    ? "border-signal-green text-signal-green bg-signal-green-dim"
    : event.kind === "phase_complete"
    ? "border-ai text-ai bg-ai-dim"
    : "border-border-strong text-ink-muted bg-surface";

  const label = event.tool
    ? (TOOL_LABELS[event.tool as ToolName] ?? event.label)
    : event.label;

  return (
    <div className="flex gap-3 min-w-0">
      {/* Spine */}
      <div className="flex flex-col items-center w-5 shrink-0">
        <div className={cn(
          "w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0",
          nodeColor
        )}>
          <NodeIcon event={event} />
        </div>
        {!isLast && <div className="flex-1 w-px bg-border mt-0.5" />}
      </div>

      {/* Content */}
      <div className={cn("flex-1 min-w-0 flex items-center gap-2 flex-wrap", isLast ? "pb-0" : "pb-3.5")}>
        <span className={cn(
          "text-xs",
          isPhase ? "font-semibold" : "font-medium",
          event.isError ? "text-signal-red" :
          event.kind === "phase_complete" ? "text-ai" : "text-ink"
        )}>
          {label}
        </span>
        {event.confidence && (
          <ConfidenceBadge level={event.confidence as ConfidenceLevel} showLabel={false} />
        )}
        {event.durationMs !== undefined && (
          <span className="text-xs text-ink-muted font-mono">
            {formatDuration(event.durationMs)}
          </span>
        )}
      </div>
    </div>
  );
}

interface OrchestrationTimelineProps {
  state: OrchestrationState;
  className?: string;
}

export function OrchestrationTimeline({ state, className }: OrchestrationTimelineProps) {
  const events = deriveTimeline(state);
  if (events.length === 0) return null;

  return (
    <div
      className={cn("space-y-0", className)}
      role="list"
      aria-label="Orchestration timeline"
    >
      {events.map((event, i) => (
        <div key={event.id} role="listitem">
          <TimelineRow event={event} isLast={i === events.length - 1} />
        </div>
      ))}
    </div>
  );
}