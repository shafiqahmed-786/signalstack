import type { OrchestrationPhase, ToolName, ToolStatus } from "@/types/api";
import type { OrchestrationState } from "../types";

/** Returns true if the phase is actively processing (non-terminal, non-idle). */
export function isActivePhase(phase: OrchestrationPhase): boolean {
  return ["created", "planning", "dispatching", "synthesizing"].includes(phase);
}

/** Returns true if the phase is a terminal state. */
export function isTerminalPhase(phase: OrchestrationPhase): boolean {
  return ["completed", "partial", "failed", "cancelled"].includes(phase);
}

/** Map SSE event name → OrchestrationPhase. Returns null for tool-level events. */
export function eventNameToPhase(event: string): OrchestrationPhase | null {
  const map: Record<string, OrchestrationPhase> = {
    "report.created": "created",
    "report.planning": "planning",
    "report.dispatching": "dispatching",
    "report.synthesizing": "synthesizing",
    "report.completed": "completed",
    "report.partial": "partial",
    "report.failed": "failed",
  };
  return map[event] ?? null;
}

/**
 * Compute a deterministic 0–1 progress value for a given phase.
 * Used by progress bars and skeleton loaders.
 */
export function phaseToProgress(phase: OrchestrationPhase): number {
  const map: Record<OrchestrationPhase, number> = {
    idle: 0,
    created: 0.05,
    planning: 0.18,
    dispatching: 0.55,
    synthesizing: 0.85,
    completed: 1,
    partial: 1,
    failed: 1,
  };
  return map[phase] ?? 0;
}

/** Elapsed ms from stream start to now (or to completedAt if finished). */
export function computeElapsedMs(state: OrchestrationState): number | null {
  if (!state.startedAt) return null;
  return (state.completedAt ?? Date.now()) - state.startedAt;
}

/** Human-readable single-line outcome description for a finished orchestration. */
export function describeOutcome(state: OrchestrationState): string {
  if (state.phase === "completed") {
    const n = state.tools.filter((t) => t.state === "completed").length;
    return `${n} data source${n !== 1 ? "s" : ""} synthesised`;
  }
  if (state.phase === "partial") {
    const failed = state.tools.filter((t) => t.state === "failed").length;
    return `${failed} source${failed !== 1 ? "s" : ""} unavailable — partial report`;
  }
  if (state.phase === "failed") {
    return state.error ?? "Pipeline failed";
  }
  return "";
}

/** Return the count of tools in each state for a quick summary. */
export function toolStateCounts(tools: ToolStatus[]): {
  running: number;
  completed: number;
  failed: number;
  pending: number;
} {
  return tools.reduce(
    (acc, t) => ({ ...acc, [t.state]: acc[t.state as keyof typeof acc] + 1 }),
    { running: 0, completed: 0, failed: 0, pending: 0 }
  );
}