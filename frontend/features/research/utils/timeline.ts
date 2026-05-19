import type { OrchestrationState } from "../types";
import type { ToolName } from "@/types/api";

export type TimelineEventKind =
  | "phase_start"
  | "tool_started"
  | "tool_completed"
  | "tool_failed"
  | "phase_complete";

export interface TimelineEvent {
  id: string;
  kind: TimelineEventKind;
  label: string;
  tool?: ToolName;
  phase?: string;
  offsetMs: number;       // ms relative to stream start (for layout)
  durationMs?: number;    // set for tool_completed
  confidence?: string | null;
  isError?: boolean;
}

/**
 * Derive a sorted list of timeline events from OrchestrationState.
 * `offsetMs` values are wall-clock deltas from startedAt, useful for
 * rendering a proportional horizontal timeline.
 */
export function deriveTimeline(state: OrchestrationState): TimelineEvent[] {
  if (!state.startedAt) return [];

  const origin = state.startedAt;
  const events: TimelineEvent[] = [];

  // Planning phase start
  if (state.phase !== "idle" && state.phase !== "created") {
    events.push({
      id: "ev-planning",
      kind: "phase_start",
      label: "Query planned",
      phase: "planning",
      offsetMs: 0,
    });
  }

  // Tool-level events
  state.tools.forEach((tool, i) => {
    const toolStart = i * 50; // stagger display offset (not wall-clock)
    events.push({
      id: `ev-tool-start-${tool.name}`,
      kind: "tool_started",
      label: tool.name,
      tool: tool.name,
      offsetMs: toolStart,
    });

    if (tool.state === "completed" && tool.duration_ms !== null) {
      events.push({
        id: `ev-tool-done-${tool.name}`,
        kind: "tool_completed",
        label: tool.name,
        tool: tool.name,
        offsetMs: toolStart + tool.duration_ms,
        durationMs: tool.duration_ms,
        confidence: tool.confidence,
      });
    } else if (tool.state === "failed") {
      events.push({
        id: `ev-tool-fail-${tool.name}`,
        kind: "tool_failed",
        label: tool.name,
        tool: tool.name,
        offsetMs: toolStart + 5_000,
        isError: true,
      });
    }
  });

  // Synthesizing phase
  const longestTool = state.tools.reduce(
    (max, t) => Math.max(max, t.duration_ms ?? 0), 0
  );
  if (["synthesizing", "completed", "partial", "failed"].includes(state.phase)) {
    events.push({
      id: "ev-synthesizing",
      kind: "phase_start",
      label: "Synthesizing report",
      phase: "synthesizing",
      offsetMs: longestTool + 200,
    });
  }

  // Terminal event
  if (state.completedAt) {
    const totalMs = state.completedAt - origin;
    events.push({
      id: "ev-terminal",
      kind: "phase_complete",
      label: state.phase === "failed" ? "Failed" : state.phase === "partial" ? "Partial" : "Complete",
      phase: state.phase,
      offsetMs: totalMs,
      isError: state.phase === "failed",
    });
  }

  return events.sort((a, b) => a.offsetMs - b.offsetMs);
}