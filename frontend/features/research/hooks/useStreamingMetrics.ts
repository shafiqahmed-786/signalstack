"use client";

import { useCallback, useRef, useState } from "react";
import type { ToolName } from "@/types/api";

export interface StreamingMetrics {
  sessionStartedAt: number | null;
  planningDurationMs: number | null;
  dispatchDurationMs: number | null;
  synthesisDurationMs: number | null;
  totalDurationMs: number | null;
  reconnectCount: number;
  toolDurations: Partial<Record<ToolName, number>>;
}

const EMPTY: StreamingMetrics = {
  sessionStartedAt: null,
  planningDurationMs: null,
  dispatchDurationMs: null,
  synthesisDurationMs: null,
  totalDurationMs: null,
  reconnectCount: 0,
  toolDurations: {},
};

export function useStreamingMetrics() {
  const [metrics, setMetrics] = useState<StreamingMetrics>(EMPTY);
  const phaseTs = useRef<Partial<Record<string, number>>>({});

  const startSession = useCallback(() => {
    const now = Date.now();
    phaseTs.current = { _session: now };
    setMetrics({ ...EMPTY, sessionStartedAt: now });
  }, []);

  const markPhaseStart = useCallback((phase: string) => {
    phaseTs.current[phase] = Date.now();
  }, []);

  const markPhaseEnd = useCallback((phase: string) => {
    const start = phaseTs.current[phase];
    if (!start) return;
    const ms = Date.now() - start;

    setMetrics((m) => ({
      ...m,
      ...(phase === "planning"     ? { planningDurationMs: ms }  : {}),
      ...(phase === "dispatching"  ? { dispatchDurationMs: ms }  : {}),
      ...(phase === "synthesizing" ? { synthesisDurationMs: ms } : {}),
      ...((phase === "completed" || phase === "partial" || phase === "failed") && m.sessionStartedAt
        ? { totalDurationMs: Date.now() - m.sessionStartedAt }
        : {}),
    }));
  }, []);

  const recordTool = useCallback((tool: ToolName, durationMs: number) => {
    setMetrics((m) => ({
      ...m,
      toolDurations: { ...m.toolDurations, [tool]: durationMs },
    }));
  }, []);

  const recordReconnect = useCallback(() => {
    setMetrics((m) => ({ ...m, reconnectCount: m.reconnectCount + 1 }));
  }, []);

  const reset = useCallback(() => {
    phaseTs.current = {};
    setMetrics(EMPTY);
  }, []);

  return { metrics, startSession, markPhaseStart, markPhaseEnd, recordTool, recordReconnect, reset };
}