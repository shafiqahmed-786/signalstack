"use client";

import { Loader2, CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";
import { PHASE_LABELS } from "@/features/research/types";
import { phaseToProgress } from "@/features/research/utils/orchestrationEvents";
import type { OrchestrationPhase } from "@/types/api";

interface Props {
  phase: OrchestrationPhase;
  compact?: boolean;
  disconnected?: boolean;
  className?: string;
}

export function StreamingStatusIndicator({
  phase,
  compact = false,
  disconnected = false,
  className,
}: Props) {
  if (phase === "idle") return null;

  const isActive = ["created", "planning", "dispatching", "synthesizing"].includes(phase);
  const isSuccess = phase === "completed" || phase === "partial";
  const isFailed = phase === "failed";
  const progress = phaseToProgress(phase);

  if (compact) {
    return (
      <span
        role="status"
        aria-live="polite"
        aria-label={PHASE_LABELS[phase]}
        className={cn(
          "inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-mono border",
          isActive   ? "border-ai/30 bg-ai-glow text-ai" :
          isSuccess  ? "border-signal-green/30 bg-signal-green-dim text-signal-green" :
          isFailed   ? "border-signal-red/30 bg-signal-red-dim text-signal-red" :
                       "border-border bg-surface text-ink-muted",
          className
        )}
      >
        <span
          className={cn(
            "w-1.5 h-1.5 rounded-full shrink-0",
            isActive  ? "bg-ai animate-pulse-ai" :
            isSuccess ? "bg-signal-green" :
            isFailed  ? "bg-signal-red" : "bg-ink-muted"
          )}
        />
        {disconnected ? "Reconnecting…" : PHASE_LABELS[phase]}
      </span>
    );
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn("space-y-2", className)}
    >
      <div className={cn(
        "flex items-center gap-2.5 px-3 py-2.5 rounded-xl border",
        isActive  ? "border-ai/25 bg-ai-glow" :
        isSuccess ? "border-signal-green/20 bg-signal-green-dim" :
        isFailed  ? "border-signal-red/20 bg-signal-red-dim" :
                    "border-border bg-surface"
      )}>
        {disconnected ? (
          <AlertTriangle className="w-4 h-4 text-signal-amber shrink-0" />
        ) : isActive ? (
          <Loader2 className="w-4 h-4 text-ai animate-spin shrink-0" />
        ) : isSuccess ? (
          <CheckCircle2 className="w-4 h-4 text-signal-green shrink-0" />
        ) : (
          <XCircle className="w-4 h-4 text-signal-red shrink-0" />
        )}

        <span className={cn(
          "text-sm font-medium flex-1",
          isActive  ? "text-ai" :
          isSuccess ? "text-signal-green" :
          isFailed  ? "text-signal-red" : "text-ink"
        )}>
          {disconnected ? "Reconnecting to stream…" : PHASE_LABELS[phase]}
        </span>

        {isActive && !disconnected && (
          <span className="flex gap-0.5 shrink-0" aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1 h-1 rounded-full bg-ai animate-pulse-ai"
                style={{ animationDelay: `${i * 180}ms` }}
              />
            ))}
          </span>
        )}
      </div>

      {/* Progress bar — only shown during active phases */}
      {isActive && (
        <div className="h-0.5 w-full rounded-full bg-surface overflow-hidden" aria-hidden="true">
          <div
            className="h-full bg-ai rounded-full transition-all duration-700 ease-out"
            style={{ width: `${progress * 100}%` }}
          />
        </div>
      )}
    </div>
  );
}