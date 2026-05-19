import { create } from "zustand";
import { devtools } from "zustand/middleware";
import type { OrchestrationState, } from "../types";
import type { ToolName, ConfidenceLevel, ReportStatus } from "@/types/api";

const INITIAL_ORCHESTRATION: OrchestrationState = {
  phase: "idle",
  reportId: null,
  plan: null,
  tools: [],
  toolsSucceeded: 0,
  toolsFailed: 0,
  error: null,
  startedAt: null,
  completedAt: null,
};

interface ResearchStore {
  orchestration: OrchestrationState;
  activeReportId: string | null;
  isStreaming: boolean;

  // Actions
  startStream: (query: string) => void;
  handleSSEEvent: (event: string, data: unknown) => void;
  resetOrchestration: () => void;
  setActiveReport: (id: string | null) => void;
}

export const useResearchStore = create<ResearchStore>()(
  devtools(
    (set, get) => ({
      orchestration: INITIAL_ORCHESTRATION,
      activeReportId: null,
      isStreaming: false,

      startStream: () => {
        set({
          isStreaming: true,
          orchestration: { ...INITIAL_ORCHESTRATION, phase: "created", startedAt: Date.now() },
        });
      },

      handleSSEEvent: (event, data) => {
        const d = data as Record<string, unknown>;

        set((state) => {
          const orch = { ...state.orchestration };

          if (event.startsWith("report.")) {
            const status = d.status as ReportStatus;
            orch.phase = status as OrchestrationState["phase"];
            if (d.report_id) orch.reportId = d.report_id as string;

            if (status === "dispatching" && d.plan) {
              const plan = d.plan as { companies: string[]; intent: string; tools: ToolName[] };
              orch.plan = plan;
              orch.tools = plan.tools.map((t) => ({
                name: t,
                state: "pending" as const,
                confidence: null,
                duration_ms: null,
                error: null,
              }));
            }

            if (status === "synthesizing") {
              orch.toolsSucceeded = (d.tools_succeeded as number) ?? 0;
              orch.toolsFailed = (d.tools_failed as number) ?? 0;
            }

            if (status === "completed" || status === "partial") {
              orch.completedAt = Date.now();
              return { orchestration: orch, isStreaming: false, activeReportId: orch.reportId };
            }

            if (status === "failed") {
              orch.error = (d.error as string) ?? "Research failed";
              orch.completedAt = Date.now();
              return { orchestration: orch, isStreaming: false };
            }
          }

          if (event === "tool.started") {
            const toolName = d.tool as ToolName;
            orch.tools = orch.tools.map((t) =>
              t.name === toolName ? { ...t, state: "running" as const } : t
            );
          }

          if (event === "tool.completed") {
            const toolName = d.tool as ToolName;
            orch.tools = orch.tools.map((t) =>
              t.name === toolName
                ? { ...t, state: "completed" as const, confidence: d.confidence as ConfidenceLevel, duration_ms: d.duration_ms as number }
                : t
            );
          }

          if (event === "tool.failed") {
            const toolName = d.tool as ToolName;
            orch.tools = orch.tools.map((t) =>
              t.name === toolName
                ? { ...t, state: "failed" as const, error: d.error as string }
                : t
            );
          }

          return { orchestration: orch };
        });
      },

      resetOrchestration: () => {
        set({ orchestration: INITIAL_ORCHESTRATION, isStreaming: false });
      },

      setActiveReport: (id) => set({ activeReportId: id }),
    }),
    { name: "research-store" }
  )
);