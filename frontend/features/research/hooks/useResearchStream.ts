"use client";

import { useCallback, useRef } from "react";
import { useAuth } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { startResearchStream } from "../api/sse";
import { useResearchStore } from "../store/researchStore";

export function useResearchStream() {
  const { getToken } = useAuth();
  const router = useRouter();
  const abortRef = useRef<AbortController | null>(null);
  const { startStream, handleSSEEvent, resetOrchestration, orchestration, isStreaming } =
    useResearchStore();

  const submitQuery = useCallback(
    async (query: string, companies?: string[]) => {
      // Cancel any in-flight stream
      abortRef.current?.abort();
      resetOrchestration();

      const token = await getToken();
      if (!token) throw new Error("Not authenticated");

      startStream(query);

      abortRef.current = await startResearchStream({
        token,
        query,
        companies,
        onEvent: handleSSEEvent,
        onComplete: () => {
          // Navigate to the completed report
          const { reportId } = useResearchStore.getState().orchestration;
          if (reportId) {
            router.push(`/research/${reportId}`);
          }
        },
        onError: (err) => {
          handleSSEEvent("report.failed", {
            status: "failed",
            error: err.message,
          });
        },
      });
    },
    [getToken, router, startStream, handleSSEEvent, resetOrchestration]
  );

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
    resetOrchestration();
  }, [resetOrchestration]);

  return {
    submitQuery,
    cancelStream,
    orchestration,
    isStreaming,
  };
}