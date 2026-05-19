"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@clerk/nextjs";
import { fetchReport, fetchReportStatus } from "../api/client";
import { reportKeys } from "./useReports";
import type { ReportDetail } from "@/types/api";

/** Full report detail including structured ResearchReport JSON. */
export function useReport(reportId: string | null) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: reportKeys.detail(reportId ?? ""),
    queryFn: async (): Promise<ReportDetail> => {
      const token = await getToken();
      if (!token || !reportId) throw new Error("Not authenticated or missing report ID");
      return fetchReport(token, reportId);
    },
    enabled: !!reportId,
    staleTime: 60_000,
  });
}

/**
 * Lightweight status-only query.
 * Auto-polls every 2 s until the report reaches a terminal state,
 * then stops polling automatically.
 */
export function useReportStatus(reportId: string | null, pollEnabled = true) {
  const { getToken } = useAuth();

  return useQuery({
    queryKey: [...reportKeys.detail(reportId ?? ""), "status"],
    queryFn: async () => {
      const token = await getToken();
      if (!token || !reportId) throw new Error("Not authenticated");
      return fetchReportStatus(token, reportId);
    },
    enabled: !!reportId && pollEnabled,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (!status) return 2_000;
      const terminal = new Set(["completed", "partial", "failed", "cancelled"]);
      return terminal.has(status) ? false : 2_000;
    },
    staleTime: 0,
  });
}

/** Returns a callback that invalidates a single report's cached data. */
export function useInvalidateReport() {
  const qc = useQueryClient();
  return (reportId: string) => {
    qc.invalidateQueries({ queryKey: reportKeys.detail(reportId) });
    qc.invalidateQueries({ queryKey: reportKeys.all });
  };
}