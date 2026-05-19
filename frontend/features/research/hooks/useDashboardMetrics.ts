"use client";

import { useMemo } from "react";
import { useReports } from "./useReports";
import type { ReportStatus, ReportSummary } from "@/types/api";

export interface DashboardMetrics {
  total: number;
  byStatus: Partial<Record<ReportStatus, number>>;
  avgProcessingMs: number | null;
  cacheHitRate: number | null;
  successRate: number | null;
  recentActivity: ReportSummary[];
  isLoading: boolean;
}

export function useDashboardMetrics(): DashboardMetrics {
  const { data, isLoading } = useReports({ page_size: 50 });

  return useMemo((): DashboardMetrics => {
    if (!data) {
      return {
        total: 0,
        byStatus: {},
        avgProcessingMs: null,
        cacheHitRate: null,
        successRate: null,
        recentActivity: [],
        isLoading,
      };
    }

    const reports = data.reports;

    // Status breakdown
    const byStatus: Partial<Record<ReportStatus, number>> = {};
    for (const r of reports) {
      byStatus[r.status] = (byStatus[r.status] ?? 0) + 1;
    }

    // Average processing time for terminal successful reports
    const finished = reports.filter(
      (r) =>
        (r.status === "completed" || r.status === "partial") &&
        r.processing_time_ms !== null
    );
    const avgProcessingMs =
      finished.length > 0
        ? finished.reduce((s, r) => s + (r.processing_time_ms ?? 0), 0) / finished.length
        : null;

    // Cache hit rate
    const cacheHitRate =
      reports.length > 0
        ? reports.filter((r) => r.cache_hit).length / reports.length
        : null;

    // Success rate (completed + partial vs total terminal)
    const terminal = reports.filter((r) =>
      ["completed", "partial", "failed"].includes(r.status)
    );
    const successRate =
      terminal.length > 0
        ? terminal.filter((r) => r.status !== "failed").length / terminal.length
        : null;

    return {
      total: data.total,
      byStatus,
      avgProcessingMs,
      cacheHitRate,
      successRate,
      recentActivity: reports.slice(0, 5),
      isLoading,
    };
  }, [data, isLoading]);
}